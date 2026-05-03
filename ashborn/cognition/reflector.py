from phoenix.framework.agent.cognition import Reflector
import json
import re

class AshbornReflector(Reflector):
    """
    Evaluates whether a single task has been successfully completed.
    """
    SYSTEM_INSTRUCTION = (
        "You are the ASHBORN Reflector. Evaluate if ONE task was completed successfully.\n"
        "Rules:\n"
        "- If the task required creating files and the tool result shows success: mark complete.\n"
        "- If files are missing, placeholders were used, or an error occurred: NOT complete.\n"
        "- If the task was a terminal command and it ran without error: complete.\n"
        "Respond ONLY with JSON: {\"is_complete\": bool, \"reflection\": \"<one sentence>\"}"
    )

    # Success patterns (no LLM needed)
    _SUCCESS_RE = re.compile(
        r'(?:successfully|created|updated|applied|done|complete|opened|installed|ran|executed)',
        re.IGNORECASE
    )
    _ERROR_RE = re.compile(r'(?:^ERROR|Traceback|exception|failed|not found)', re.IGNORECASE)

    async def reflect(self, objective: str, action: dict, result: str) -> dict:
        result_str = str(result)

        # Fast path: deterministic success detection
        if self._SUCCESS_RE.search(result_str) and not self._ERROR_RE.search(result_str):
            return {"is_complete": True, "reflection": "Tool reported success."}

        # Fast path: clear error
        if self._ERROR_RE.search(result_str):
            return {"is_complete": False, "reflection": result_str[:200]}

        # Slow path: LLM judge only for ambiguous results
        prompt = (
            f"{self.SYSTEM_INSTRUCTION}\n\n"
            f"Task: {objective}\nResult: {result_str[:500]}\nJSON Response:"
        )
        response = await self.llm.generate(prompt, session_id=None, max_tokens=80)
        try:
            clean = response.strip()
            if "```" in clean:
                m = re.search(r'\{.*\}', clean, re.DOTALL)
                clean = m.group(0) if m else clean
            data = json.loads(clean)
            return {
                "is_complete": bool(data.get("is_complete", False)),
                "reflection": str(data.get("reflection", ""))
            }
        except Exception:
            return {"is_complete": False, "reflection": "Could not evaluate result. Continuing."}
