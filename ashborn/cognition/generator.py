import json
import re
import os
import ast
import subprocess

from .helpers.tasks import _clean_json
from .helpers.generation import _add_generation_block

class AshbornGenerator:
    """
    Receives a plan_step and generates actual code/commands iteratively.
    Produces generation_blocks mapped to the schema.
    """
    def __init__(self, llm):
        self.llm = llm

    def _validate_artifact(self, artifact: dict) -> str | None:
        """Validates the syntax of an artifact's code before execution."""
        # For file_update_multi, we might want to validate the chunks, but it's harder to validate partial python without context.
        # We will focus on full file code and terminal commands.
        if artifact.get("type") == "file_update_multi":
            edits = artifact.get("edits", [])
            if not isinstance(edits, list) or len(edits) == 0:
                return "Error: type 'file_update_multi' requires a non-empty 'edits' array."
            for i, e in enumerate(edits):
                missing = [k for k in ["StartLine", "EndLine", "TargetContent", "ReplacementContent"] if k not in e]
                if missing:
                    return f"Error in edit {i}: missing keys {missing}. Do NOT use 'old_lines' or 'new_lines'."
            return None
            
        lang = artifact.get("language", "").lower()
        code = artifact.get("code", "")
        
        if not code:
            return None
            
        if lang in ["python", "py"]:
            try:
                ast.parse(code)
            except SyntaxError as e:
                return f"Python SyntaxError: {e.msg} at line {e.lineno}"
            except Exception as e:
                return f"Python Parse Error: {str(e)}"
                
        elif lang in ["bash", "sh"] or artifact.get("type") == "terminal":
            try:
                result = subprocess.run(["bash", "-n", "-c", code], capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    return f"Bash Syntax Error: {result.stderr.strip()}"
            except Exception as e:
                return f"Bash Validation Error: {str(e)}"
                
        elif lang == "json":
            try:
                json.loads(code)
            except Exception as e:
                return f"JSON Parse Error: {str(e)}"
                
        # Path validation: Prevent absolute paths or going out of workspace
        path = artifact.get("path", "")
        if path.startswith("/") or ".." in path:
            return f"Security Error: Absolute paths or directory traversal ('..') are forbidden: {path}"
            
        return None

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

=== GENERATOR RULEBOOK ===
1. Respond ONLY with valid JSON.
2. Multi-file Generation: You SHOULD generate multiple artifacts simultaneously if they belong together logically (e.g., creating a module, an `__init__.py`, and a test file in one pass).
3. type "file_write": Use for NEW files. "code" is full content.
4. type "file_update_multi": Use for EXISTING files. Use "edits" field.
5. type "terminal": "code" is the bash command.
6. DIRECTORY AWARENESS: Always ensure directories exist before writing files.

Plan Step Details:
Step ID: {step_id} | Type: {type}
Approach: {approach}
Algorithm: {algorithm}

=== RESPONSE SCHEMA ===
{{
  "generation_blocks": [
    {{
      "generate_block_id": <INT>,
      "plan_step_id": {step_id},
      "artifacts": [
        {{
          "type": "file_write | file_update_multi | terminal",
          "path": "<path>",
          "language": "<python|bash|json|etc>",
          "code": "...",
          "edits": []
        }}
      ],
      "status": "success",
      "metadata": {{ "model": "ashborn-generator" }}
    }}
  ]
}}

Existing File Context:
{file_context}
"""

    async def generate_step(self, step: dict, task: dict) -> dict:
        from .helpers.schemas import validate_schema, GENERATION_SCHEMA
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
            
        base_prompt = self.GENERATION_PROMPT.format(
            step_id=step.get("plan_step_id", 1),
            type=step.get("type", ""),
            approach=step.get("solution", {}).get("approach", ""),
            algorithm=step.get("solution", {}).get("algorithm", ""),
            file_context=file_context or "No existing files detected."
        )

        MAX_ATTEMPTS = 2
        validation_errors = []
        gen_data = {"generation_blocks": []}
        
        for attempt in range(MAX_ATTEMPTS):
            prompt = base_prompt
            if validation_errors:
                err_str = "\n".join(f"- {e}" for e in validation_errors)
                prompt += f"\n\n=== PREVIOUS ATTEMPT FAILED SYNTAX VALIDATION ===\nFix these errors:\n{err_str}\n"

            response = await self.llm.generate(prompt, session_id=None)
            clean = _clean_json(response)
            
            try:
                gen_data = json.loads(clean)
            except Exception as e:
                m = re.search(r'\{.*\}', clean, re.DOTALL)
                if m:
                    try:
                        gen_data = json.loads(m.group(0))
                    except Exception:
                        gen_data = {"generation_blocks": []}
                else:
                    gen_data = {"generation_blocks": []}

            # Schema Validation
            errors = validate_schema(gen_data, GENERATION_SCHEMA)
            if errors:
                validation_errors.extend(errors)

            # Run Syntax Validation Layer
            validation_errors = []
            blocks = gen_data.get("generation_blocks", [])
            for b in blocks:
                for art in b.get("artifacts", []):
                    err = self._validate_artifact(art)
                    if err:
                        validation_errors.append(f"In {art.get('path', 'unknown')}: {err}")
            
            if not validation_errors:
                break # Success!
                
        if validation_errors:
            # If we exhausted attempts and still have errors, return a syntax_error status block
            return {
                "generation_blocks": [{
                    "plan_step_id": step.get("plan_step_id"),
                    "artifacts": [],
                    "status": "syntax_error",
                    "error": "\n".join(validation_errors)
                }]
            }

        # Persist valid blocks
        blocks = gen_data.get("generation_blocks", [])
        for b in blocks:
            b["plan_step_id"] = step.get("plan_step_id")
            _add_generation_block(b)
            
        return gen_data
