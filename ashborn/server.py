import asyncio
import json
import uuid
import logging
import os
from contextlib import asynccontextmanager
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

# ── IPC Context ───────────────────────────────────────────────────────────────
# Allows tools to access the VS Code IPC bridge for the current request
vscode_ipc_context: ContextVar[Optional[callable]] = ContextVar("vscode_ipc", default=None)

# Thread-safe queue for file-open requests emitted by sync tools
from collections import deque
_pending_file_opens: deque = deque()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)s  %(name)s — %(message)s"
)
log = logging.getLogger("ashborn.server")

# ── Global agent & IPC ────────────────────────────────────────────────────────
_agent = None
# Stores Futures for tool calls waiting for VS Code response: { tool_call_id: Future }
_ipc_responses = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.warning(f"🔥 Ashborn Server starting in {os.getcwd()} …")
    # Start agent initialization in the background
    asyncio.create_task(_initialize_agent())
    yield
    log.warning("🛑 Ashborn Agent server shut down.")

async def _initialize_agent():
    global _agent
    try:
        from ashborn.agent import get_ashborn_agent
        log.warning("🧠 Loading AI modules & Phoenix framework…")
        _agent = await get_ashborn_agent()
        log.warning("✅ Ashborn Agent is now READY.")
    except Exception as exc:
        log.error(f"❌ Failed to initialize agent: {exc}", exc_info=True)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Ashborn Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    task: str
    session_id: Optional[str] = None
    mode: str = "auto"   # "auto" | "plan" | "fast_ans"

class ToolResult(BaseModel):
    call_id: str
    result: str

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "agent_ready": _agent is not None}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream agent response as Server-Sent Events."""
    if _agent is None:
        async def _error():
            yield f"data: {json.dumps({'type':'error','content':'Agent not ready.'})}\n\n"
        return StreamingResponse(_error(), media_type="text/event-stream")

    session_id = req.session_id or str(uuid.uuid4())
    queue = asyncio.Queue()

    async def _emit_event(event: dict):
        await queue.put(event)

    async def _vscode_call(tool_name: str, arguments: dict) -> str:
        call_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        _ipc_responses[call_id] = future
        
        # Emit the tool request to the frontend
        await _emit_event({
            "type": "vscode_tool",
            "call_id": call_id,
            "tool": tool_name,
            "arguments": arguments
        })
        
        try:
            return await asyncio.wait_for(future, timeout=60.0)
        except asyncio.TimeoutError:
            return "ERROR: VS Code tool call timed out."
        finally:
            _ipc_responses.pop(call_id, None)

    async def _run_agent():
        # Set the IPC context for this specific task
        token = vscode_ipc_context.set(_vscode_call)
        try:
            async for event in _agent.run_stream(
                req.task, session_id=session_id, mode=req.mode
            ):
                await queue.put(event)
        except Exception as exc:
            log.exception("Stream error")
            await queue.put({"type": "error", "content": str(exc)})
        finally:
            vscode_ipc_context.reset(token)
            await queue.put({"type": "done"})

    async def _generate():
        # Start the agent task in the background
        agent_task = asyncio.create_task(_run_agent())
        
        # Always send session ID first
        yield f"data: {json.dumps({'type':'session','session_id':session_id})}\n\n"
        
        while True:
            # Flush any pending file-open events from sync tools
            while _pending_file_opens:
                file_path = _pending_file_opens.popleft()
                yield f"data: {json.dumps({'type':'vscode_tool','call_id':'noop','tool':'open_file','arguments':{'path': file_path}})}\n\n"

            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "done":
                break
        
        await agent_task

    return StreamingResponse(_generate(), media_type="text/event-stream")


@app.post("/tool/result")
async def tool_result(res: ToolResult):
    """Receive results for pending VS Code tool calls."""
    if res.call_id in _ipc_responses:
        _ipc_responses[res.call_id].set_result(res.result)
        return {"status": "ok"}
    return {"status": "error", "message": "Call ID not found or already timed out."}


@app.post("/reset")
async def reset_session():
    return {"status": "reset"}


# ── Configuration Management ──────────────────────────────────────────────────
class ConfigUpdate(BaseModel):
    settings: dict

@app.get("/config")
async def get_config():
    """Returns current environment variables for Ashborn."""
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Reload to get fresh values
    load_dotenv(override=True)
    
    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", ""),
        "OPENAI_LLM_MODEL": os.getenv("OPENAI_LLM_MODEL", "gpt-4o"),
        "ASHBORN_LOG_LEVEL": os.getenv("LOG_LEVEL", "WARNING"),
    }

@app.post("/config")
async def update_config(update: ConfigUpdate):
    """Updates the .env file with new settings."""
    from pathlib import Path
    env_path = Path(".env")
    
    # Read existing lines
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    
    new_settings = update.settings
    updated_keys = set()
    
    new_lines = []
    for line in lines:
        if "=" in line and not line.startswith("#"):
            key = line.split("=")[0].strip()
            if key in new_settings:
                new_lines.append(f"{key}={new_settings[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)
    
    # Add new keys
    for key, val in new_settings.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}")
            
    env_path.write_text("\n".join(new_lines) + "\n")
    
    # Trigger agent re-initialization
    global _agent
    from ashborn.agent import get_ashborn_agent
    from dotenv import load_dotenv
    load_dotenv(override=True)
    _agent = await get_ashborn_agent()
    
    return {"status": "ok", "message": "Configuration updated and agent re-initialized."}


# ── Text-to-Speech ────────────────────────────────────────────────────────────
class TTSRequest(BaseModel):
    text: str
    lang: str = "en"

@app.post("/tts")
async def text_to_speech(req: TTSRequest):
    """Generate speech from text using gTTS and return base64-encoded MP3."""
    import io
    import base64
    try:
        from gtts import gTTS
    except ImportError:
        return {"status": "error", "message": "gTTS not installed. Run: pip install gtts"}

    try:
        # Truncate to avoid huge audio files
        text = req.text[:1000].strip()
        tts = gTTS(text=text, lang=req.lang, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_b64 = base64.b64encode(buf.read()).decode("utf-8")
        return {"status": "ok", "audio": audio_b64}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

# ── Speech-to-Text ────────────────────────────────────────────────────────────
import subprocess

_recording_process = None
_recording_file = "/tmp/ashborn_recording.wav"

@app.post("/stt/start")
async def start_recording():
    """Start recording audio using arecord."""
    global _recording_process
    
    if _recording_process is not None:
        try:
            _recording_process.terminate()
            _recording_process.wait(timeout=2)
        except:
            pass
        _recording_process = None
        
    try:
        _recording_process = subprocess.Popen(
            ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "-q", _recording_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"status": "ok", "message": "Recording started"}
    except Exception as exc:
        return {"status": "error", "message": f"Failed to start arecord: {exc}"}

@app.post("/stt/stop")
async def stop_recording():
    """Stop recording and transcribe using SpeechRecognition (Google API)."""
    global _recording_process
    
    if _recording_process is not None:
        try:
            _recording_process.terminate()
            _recording_process.wait(timeout=2)
        except:
            pass
        _recording_process = None
        
    if not os.path.exists(_recording_file):
        return {"status": "error", "message": "No recording file found"}
        
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(_recording_file) as source:
            audio = recognizer.record(source)
            
        text = recognizer.recognize_google(audio)
        return {"status": "ok", "text": text}
    except ImportError:
        return {"status": "error", "message": "SpeechRecognition not installed. Run: pip install SpeechRecognition"}
    except sr.UnknownValueError:
        return {"status": "error", "message": "Could not understand audio. Please try again."}
    except sr.RequestError as e:
        return {"status": "error", "message": f"Could not request results; {e}"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

# ── CLI entry ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ashborn.server:app", host="127.0.0.1", port=8765, reload=False)
