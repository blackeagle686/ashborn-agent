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

# ── Global agent ──────────────────────────────────────────────────────────────
_agent = None

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

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "agent_ready": _agent is not None}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream agent response as Server-Sent Events."""

    if _agent is None:
        async def _error():
            yield f"data: {json.dumps({'type':'error','content':'Agent not ready — check server logs.'})}\n\n"
        return StreamingResponse(_error(), media_type="text/event-stream")

    session_id = req.session_id or str(uuid.uuid4())

    async def _generate():
        # First frame: send back the session_id so the client can track it
        yield f"data: {json.dumps({'type':'session','session_id':session_id})}\n\n"
        try:
            async for event in _agent.run_stream(
                req.task, session_id=session_id, mode=req.mode
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            yield f"data: {json.dumps({'type':'status','content':'⏹ Stopped.'})}\n\n"
        except Exception as exc:
            log.exception("Stream error")
            yield f"data: {json.dumps({'type':'error','content':str(exc)})}\n\n"
        finally:
            yield f"data: {json.dumps({'type':'done'})}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/reset")
async def reset_session():
    """Reset — client should discard its session_id after calling this."""
    return {"status": "reset"}


# ── CLI entry ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ashborn.server:app", host="127.0.0.1", port=8765, reload=False)
