"""
Ashborn Backend — Code completion & code-action endpoints.
"""
from fastapi import APIRouter

from .state import log
from .schemas import CompletionRequest, CodeActionRequest

router = APIRouter()

_completion_llm = None


async def _get_completion_llm():
    global _completion_llm
    if _completion_llm is None:
        try:
            from phoenix.services.llm.openai import OpenAILLM
            _completion_llm = OpenAILLM()
            await _completion_llm.init()
        except ImportError:
            log.error("Could not import OpenAILLM from phoenix.")
    return _completion_llm


@router.post("/completion")
async def code_completion(req: CompletionRequest):
    """Generate inline code completions using Phoenix OpenAILLM."""
    llm = await _get_completion_llm()
    if not llm:
        return {"status": "error", "message": "Completion LLM not available."}

    prompt = f"""You are an elite AI inline code completion engine.
Your task is to predict exactly what code should be inserted at the cursor position.
Provide ONLY the raw code to be inserted. DO NOT include markdown formatting, backticks, or any conversational text.

File: {req.file_path}

Context before cursor:
{req.content_before[-1500:]}

<cursor>

Context after cursor:
{req.content_after[:1500]}
"""
    try:
        response = await llm.generate(prompt, max_tokens=150)
        clean = response.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
        if clean.endswith("```"):
            clean = "\n".join(clean.split("\n")[:-1])
        return {"status": "ok", "completion": clean}
    except Exception as e:
        log.error(f"Completion failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/code_action")
async def code_action(req: CodeActionRequest):
    """Process context menu AI code actions."""
    llm = await _get_completion_llm()
    if not llm:
        return {"status": "error", "message": "LLM not available."}

    action_prompts = {
        "explain": "Explain what this code does in a concise, technical manner. Do not provide code blocks, just explain.",
        "refactor": "Refactor this code to improve readability and maintainability. Return ONLY the new code snippet, with NO markdown formatting.",
        "optimize": "Optimize this code for performance. Return ONLY the new code snippet, with NO markdown formatting.",
        "fix": "Fix any bugs or issues in this code. Return ONLY the new code snippet, with NO markdown formatting.",
    }

    instruction = action_prompts.get(req.action, "Process this code.")

    prompt = f"""You are an elite AI developer agent.
{instruction}

File: {req.file_path}

Context:
{req.full_text[:3000]}

Selected Code:
{req.selected_text}
"""
    try:
        response = await llm.generate(prompt, max_tokens=1000)
        clean = response.strip()
        if req.action in ["refactor", "optimize", "fix"]:
            if clean.startswith("```"):
                clean = "\n".join(clean.split("\n")[1:])
            if clean.endswith("```"):
                clean = "\n".join(clean.split("\n")[:-1])
        return {"status": "ok", "result": clean.strip()}
    except Exception as e:
        log.error(f"Code action failed: {e}")
        return {"status": "error", "message": str(e)}
