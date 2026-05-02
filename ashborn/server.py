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
    global _agent
    log.warning(f"🔥 Initializing Ashborn Agent in {os.getcwd()} …")
    try:
        from ashborn.agent import get_ashborn_agent
        _agent = await get_ashborn_agent()
        log.warning("✅ Ashborn Agent ready.")
    except Exception as exc:
        log.error(f"❌ Failed to initialize agent: {exc}", exc_info=True)
    yield
    log.warning("🛑 Ashborn Agent server shut down.")

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


# ── CLI entry ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ashborn.server:app", host="127.0.0.1", port=8765, reload=False)
