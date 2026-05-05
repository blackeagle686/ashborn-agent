from phoenix.framework.agent.cognition import Reflector
import json
import re

from ..core.prompts import build_reflector_prompt

class AshbornReflector(Reflector):
    """Evaluates whether a single task has been successfully completed."""

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
        prompt = build_reflector_prompt(objective, result_str)
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
