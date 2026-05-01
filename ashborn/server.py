"""
Ashborn Agent — FastAPI Server
Exposes the agent via HTTP + Server-Sent Events for the VS Code extension.
Run: uvicorn ashborn.server:app --host 127.0.0.1 --port 8765
"""
import asyncio
import json
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

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
    log.warning("🔥 Initializing Ashborn Agent …")
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

# ── IPC Helper ────────────────────────────────────────────────────────────────
async def call_vscode_tool(tool_name: str, arguments: dict) -> str:
    """Used by agent tools to request info from VS Code."""
    call_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    _ipc_responses[call_id] = future

    # The actual emission happens via the active SSE stream. 
    # We rely on the agent emitting a 'vscode_tool' event.
    # (The agent logic in cognition/planner.py will handle this)
    
    try:
        # Wait for the /tool/result endpoint to fulfill this future
        # Timeout after 60s
        return await asyncio.wait_for(future, timeout=60.0)
    except asyncio.TimeoutError:
        return "ERROR: VS Code tool call timed out."
    finally:
        _ipc_responses.pop(call_id, None)

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
        try:
            async for event in _agent.run_stream(
                req.task, session_id=session_id, mode=req.mode,
                context_overrides={"vscode_call": _vscode_call}
            ):
                await queue.put(event)
        except Exception as exc:
            log.exception("Stream error")
            await queue.put({"type": "error", "content": str(exc)})
        finally:
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


# ── CLI entry ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ashborn.server:app", host="127.0.0.1", port=8765, reload=False)
