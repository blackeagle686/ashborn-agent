"""
Ashborn Backend — Chat & Agent streaming endpoints.
"""
import asyncio
import json
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .state import (
    log, vscode_ipc_context, _pending_file_opens,
    get_agent, _ipc_responses,
)
from .schemas import ChatRequest, ToolResult

router = APIRouter()


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream agent response as Server-Sent Events."""
    agent = get_agent()
    if agent is None:
        async def _error():
            yield f"data: {json.dumps({'type':'error','content':'Agent not ready.'})}\n\n"
        return StreamingResponse(_error(), media_type="text/event-stream")

    session_id = req.session_id or str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()

    async def _emit_event(event: dict):
        await queue.put(event)

    async def _vscode_call(tool_name: str, arguments: dict) -> str:
        call_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        _ipc_responses[call_id] = future

        await _emit_event({
            "type": "vscode_tool",
            "call_id": call_id,
            "tool": tool_name,
            "arguments": arguments,
        })

        try:
            return await asyncio.wait_for(future, timeout=60.0)
        except asyncio.TimeoutError:
            return "ERROR: VS Code tool call timed out."
        finally:
            _ipc_responses.pop(call_id, None)

    async def _run_agent():
        token = vscode_ipc_context.set(_vscode_call)
        try:
            async for event in agent.run_stream(
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
        agent_task = asyncio.create_task(_run_agent())
        yield f"data: {json.dumps({'type':'session','session_id':session_id})}\n\n"

        while True:
            while _pending_file_opens:
                file_path = _pending_file_opens.popleft()
                yield f"data: {json.dumps({'type':'vscode_tool','call_id':'noop','tool':'open_file','arguments':{'path': file_path}})}\n\n"

            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "done":
                break

        await agent_task

    return StreamingResponse(_generate(), media_type="text/event-stream")


@router.post("/tool/result")
async def tool_result(res: ToolResult):
    """Receive results for pending VS Code tool calls."""
    if res.call_id in _ipc_responses:
        _ipc_responses[res.call_id].set_result(res.result)
        return {"status": "ok"}
    return {"status": "error", "message": "Call ID not found or already timed out."}


@router.post("/reset")
async def reset_session():
    return {"status": "reset"}
