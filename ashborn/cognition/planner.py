from phoenix.framework.agent.cognition import Planner
import json
import re
import os

from .tasks import _clean_json

class AshbornPlanner(Planner):
    """
    Receives one task at a time and selects the correct tools to handle it.
    """

    SYSTEM_INSTRUCTION = (
        "You are the ASHBORN Execution Engine. You receive ONE task and must execute it immediately.\n"
        "\n"
        "=== FILE OPERATION RULES (MANDATORY) ===\n"
        "NEW files (do not exist yet):\n"
        "  → Use `file_write` for creating NEW files (this tool automatically creates missing folders).\n"
        "  → Use `project_generator` ONLY for large boilerplate scaffolding.\n"
        "EXISTING files (already on disk):\n"
        "  → FORBIDDEN: `file_write` on existing files — it will overwrite everything.\n"
        "  → REQUIRED: `file_update_multi` for surgical edits with line numbers.\n"
        "  → The file content will be provided to you with line numbers (L1:, L2:, ...).\n"
        "  → Specify only the lines that MUST change. Leave everything else untouched.\n"
        "  → Prefer line_start/line_end edits when you know the range; use search/replace for single-line changes.\n"
        "\n"
        "=== OTHER TOOLS ===\n"
        "3. INFRASTRUCTURE: Use `terminal` for pip install, git, mkdir, etc.\n"
        "4. READING/INSPECTING: Use `file_read_lines` to read with line numbers.\n"
        "\n"
        "Rule: Output only the tool calls needed. Finish only after verifiable success."
    )

    # ── File path detection ────────────────────────────────────────────────────
    _FILE_PATH_RE = re.compile(
        r'(?:^|\s|["\'])'
        r'([\w./\-]+\.(?:py|js|ts|jsx|tsx|json|yaml|yml|toml|txt|md|sh|env|cfg|ini|html|css|sql|go|rs|java|c|cpp|h))'
        r'(?:$|\s|["\'])',
        re.MULTILINE
    )

    def _detect_existing_files(self, task: dict) -> list:
        """Scan task title + description for file paths that actually exist on disk."""
        text = task.get("title", "") + " " + task.get("description", "")
        candidates = self._FILE_PATH_RE.findall(text)
        return [p for p in candidates if os.path.isfile(p)]

    def _read_file_for_prompt(self, file_path: str, max_lines: int = 300) -> str:
        """Read a file and return it with line numbers for injection into the LLM prompt."""
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

    @property
    def _tool_info_cached(self) -> str:
        if not hasattr(self, "_tool_info_str"):
            self._tool_info_str = json.dumps(self.tools.get_all_tools_info(), indent=2)
        return self._tool_info_str

    def _build_task_prompt(self, task: dict, previous_results: str = "",
                           file_contents: dict = None) -> str:
        tool_info = self._tool_info_cached
        task_type = task.get("type", "")

        # Build file context section
        file_context = ""
        if file_contents:
            sections = []
            for path, content in file_contents.items():
                sections.append(
                    f"=== EXISTING FILE: {path} ===\n"
                    f"{content}\n"
                    f"=== END OF {path} ==="
                )
            file_context = (
                "\nEXISTING FILE CONTENT (read before editing — use line numbers for edits):\n"
                + "\n\n".join(sections)
                + "\n"
            )

        # Extra reminder for modify_file tasks
        modify_reminder = ""
        if task_type == "modify_file" or file_contents:
            modify_reminder = (
                "\n⚠ MODIFY TASK — The file(s) above already exist. "
                "You MUST use `file_update_multi` with MINIMAL edits. "
                "DO NOT use `file_write` or `project_generator`. "
                "Reference exact line numbers from the file content above.\n"
            )

        return f"""{self.SYSTEM_INSTRUCTION}

AVAILABLE TOOLS:
{tool_info}

PREVIOUS RESULTS (from earlier tasks):
{previous_results or 'None'}
{file_context}{modify_reminder}
CURRENT TASK:
Type       : {task_type or 'unspecified'}
Title      : {task.get('title', '')}
Priority   : {task.get('priority', '')}
Description: {task.get('description', '')}

You MUST respond with a JSON object:
{{
    "thought": "<brief reasoning>",
    "actions": [
        {{"tool": "tool_name", "kwargs": {{"arg": "value"}} }}
    ]
}}

For task completion with no tool needed:
{{"thought": "Already done or not applicable.", "actions": [{{"tool": "finish"}}]}}

Respond ONLY with valid JSON.
"""

    def task_status_line(self, task: dict) -> str:
        """Return a deterministic status line from the task dict — no LLM call needed."""
        type_icon = {"new_file": "📄", "modify_file": "✏️", "command": "⚡", "read": "🔍"}
        icon = type_icon.get(task.get("type", ""), "⚙")
        return f"{icon} {task.get('description', task.get('title', ''))[:120]}"

    async def plan(self, objective: str, previous_results: str = "") -> dict:
        """
        Standard plan() interface — objective may be a task title string
        (injected by AshbornLoop) or a full objective.
        """
        # If called with a raw task dict serialized as string, parse it
        task = {"title": objective, "priority": 1, "description": objective}
        if objective.startswith("{"):
            try:
                task = json.loads(objective)
            except Exception:
                pass

        full_prompt = self._build_task_prompt(task, previous_results)
        response = await self.llm.generate(full_prompt, session_id=None)
        return self._parse_plan(response)

    async def plan_task(self, task: dict, previous_results: str = "") -> dict:
        """
        Two-phase task-aware planning:
          Phase 1 — If the task involves existing file(s), read them directly
                     and inject their content (with line numbers) into the prompt.
          Phase 2 — Ask the LLM to produce MINIMAL surgical edits based on the
                     actual file content it can now see.
        """
        file_contents = None
        task_type = task.get("type", "")

        # Detect existing files whenever type is modify_file OR type is unspecified
        # (we auto-detect to be safe)
        if task_type != "new_file" and task_type != "command":
            existing = self._detect_existing_files(task)
            if existing:
                file_contents = {}
                for path in existing:
                    file_contents[path] = self._read_file_for_prompt(path)

        full_prompt = self._build_task_prompt(task, previous_results, file_contents=file_contents)
        response = await self.llm.generate(full_prompt, session_id=None)
        return self._parse_plan(response)

    def _parse_plan(self, response: str) -> dict:
        clean = _clean_json(response)
        try:
            return json.loads(clean)
        except Exception:
            m = re.search(r'\{.*\}', clean, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
            if "finish" in response.lower():
                return {"actions": [{"tool": "finish"}]}
            return {"actions": []}
