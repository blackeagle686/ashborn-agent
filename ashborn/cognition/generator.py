import json
import re
import os

from .helpers.tasks import _clean_json
from .helpers.generation import _add_generation_block

class AshbornGenerator:
    """
    Receives a plan_step and generates actual code/commands iteratively.
    Produces generation_blocks mapped to the schema.
    """
    def __init__(self, llm):
        self.llm = llm

    # ── File path detection ────────────────────────────────────────────────────
    _FILE_PATH_RE = re.compile(
        r'(?:^|\s|["\'])'
        r'([\w./\-]+\.(?:py|js|ts|jsx|tsx|json|yaml|yml|toml|txt|md|sh|env|cfg|ini|html|css|sql|go|rs|java|c|cpp|h))'
        r'(?:$|\s|["\'])',
        re.MULTILINE
    )

    def _detect_existing_files(self, text: str) -> list:
        candidates = self._FILE_PATH_RE.findall(text)
        return [p for p in candidates if os.path.isfile(p)]

    def _read_file_for_prompt(self, file_path: str, max_lines: int = 300) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            total = len(lines)
            truncated = total > max_lines
            display = lines[:max_lines]
            numbered = [f"L{i+1}: {l.rstrip()}" for i, l in enumerate(display)]
            result = f"[{file_path}] — {total} lines total\n" + "\n".join(numbered)
            if truncated:
                result += f"\n... (truncated, showing first {max_lines} lines)"
            return result
        except Exception as ex:
            return f"Could not read {file_path}: {ex}"

    GENERATION_PROMPT = """\
You are the ASHBORN Code Generator. You receive ONE plan_step and must generate the exact code/files required.

Your output MUST be a JSON object conforming to this exact schema:
{{
  "generation_blocks": [
    {{
      "generate_block_id": <INT>,
      "plan_step_id": <INT>,
      "artifacts": [
        {{
          "type": "file_write" | "file_update_multi" | "terminal",
          "path": "<file path or working directory>",
          "language": "<python|bash|json|etc>",
          "code": "<full file content for file_write, or bash command for terminal>",
          "edits": [
            {{
              "AllowMultiple": false,
              "StartLine": <INT>,
              "EndLine": <INT>,
              "TargetContent": "<exact string to match>",
              "ReplacementContent": "<new string>"
            }}
          ]
        }}
      ],
      "status": "success",
      "metadata": {{
        "model": "ashborn-generator"
      }}
    }}
  ]
}}

=== FILE OPERATION RULES ===
- type "file_write": Use for NEW files. "code" is the full file content.
- type "file_update_multi": Use for EXISTING files. Use the "edits" field (JSON array of chunks). Do NOT use "code".
- type "terminal": "code" is the bash command to run.

Plan Step Details:
Step ID: {step_id}
Type: {type}
Approach: {approach}
Algorithm: {algorithm}

Existing File Context:
{file_context}

Respond ONLY with valid JSON.
"""

    async def generate_step(self, step: dict, task: dict) -> dict:
        text = step.get("solution", {}).get("approach", "") + " " + task.get("description", "")
        existing = self._detect_existing_files(text)
        
        file_context = ""
        if existing:
            sections = []
            for path in existing:
                sections.append(
                    f"=== EXISTING FILE: {path} ===\n"
                    f"{self._read_file_for_prompt(path)}\n"
                    f"=== END OF {path} ==="
                )
            file_context = "\n".join(sections)
            
        prompt = self.GENERATION_PROMPT.format(
            step_id=step.get("plan_step_id", 1),
            type=step.get("type", ""),
            approach=step.get("solution", {}).get("approach", ""),
            algorithm=step.get("solution", {}).get("algorithm", ""),
            file_context=file_context or "No existing files detected."
        )

        response = await self.llm.generate(prompt, session_id=None)
        clean = _clean_json(response)
        
        try:
            gen_data = json.loads(clean)
        except Exception:
            m = re.search(r'\{.*\}', clean, re.DOTALL)
            if m:
                gen_data = json.loads(m.group(0))
            else:
                gen_data = {"generation_blocks": []}
                
        # Persist block
        blocks = gen_data.get("generation_blocks", [])
        for b in blocks:
            # Force step id mapping
            b["plan_step_id"] = step.get("plan_step_id")
            _add_generation_block(b)
            
        return gen_data
