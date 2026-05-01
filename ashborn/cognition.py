"""
Ashborn Cognition Module — Task-File Driven Architecture.

Pipeline:
  1. AshbornThinker  → Decomposes prompt into a prioritized .ashborn_tasks.json
  2. AshbornLoop     → Reads task file, drives Planner one task at a time
  3. AshbornPlanner  → Receives a single task dict, selects tools and acts
  4. AshbornReflector → Marks task complete or requests retry
  5. AshbornLoop     → Deletes task file when all tasks are done
"""

from phoenix.framework.agent.cognition import Thinker, Planner, Reflector
from phoenix.framework.agent.core.loop import AgentLoop
from rich.console import Console
import json
import re
import os
import asyncio

console = Console()

# ── Task file path ─────────────────────────────────────────────────────────────
TASK_FILE = ".ashborn_tasks.json"


# ── Task file helpers ──────────────────────────────────────────────────────────

def _load_tasks() -> dict:
    with open(TASK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_tasks(data: dict) -> None:
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _mark_task(task_id: int, status: str) -> None:
    data = _load_tasks()
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            break
    _save_tasks(data)


def _clean_json(raw: str) -> str:
    """Strip markdown fences and return bare JSON."""
    s = raw.strip()
    if "```json" in s:
        s = s.split("```json")[1].split("```")[0].strip()
    elif "```" in s:
        s = s.split("```")[1].split("```")[0].strip()
    return s


# ── 1. Thinker ─────────────────────────────────────────────────────────────────

class AshbornThinker(Thinker):
    """
    Decomposes the user prompt into a prioritized task list
    and writes it to .ashborn_tasks.json.
    Returns the task file path so the loop knows where to find it.
    """

    TASK_GENERATION_PROMPT = """\
You are ASHBORN — The Great Architect. Your job is to decompose a user request \
into a precise, prioritized list of implementation tasks.

Rules:
- Each task must be ATOMIC: one clear action (create a file, edit a file, run a command).
- Priority 1 = must happen first (e.g. create folder structure, install deps).
- Higher numbers = later tasks that depend on earlier ones.
- Write descriptions that tell the executor EXACTLY what to build/do.
- No fluff. No meta-commentary. Only tasks.
- For the "type" field use EXACTLY one of: new_file | modify_file | command | read
  • new_file   — creating a file that does NOT yet exist
  • modify_file — editing/patching a file that already exists
  • command    — a shell/terminal command
  • read       — reading or inspecting only

User Request:
{prompt}

Context:
{context}

Respond ONLY with a valid JSON object in this exact format:
{{
    "original_prompt": "<user request>",
    "tasks": [
        {{
            "id": 1,
            "priority": 1,
            "type": "<new_file|modify_file|command|read>",
            "title": "<short title>",
            "description": "<detailed implementation instruction>",
            "status": "pending"
        }}
    ]
}}
"""

    async def analyze(self, prompt: str, memory, session_id: str) -> str:
        context = await memory.get_full_context(session_id, query=prompt)

        full_prompt = self.TASK_GENERATION_PROMPT.format(
            prompt=prompt,
            context=context or "No prior context."
        )

        raw = await self.llm.generate(full_prompt, session_id=None, max_tokens=1500)
        clean = _clean_json(raw)

        # Parse the task list
        try:
            task_data = json.loads(clean)
        except Exception:
            # Aggressive fallback: grab the first {...} block
            m = re.search(r'\{.*\}', clean, re.DOTALL)
            if m:
                task_data = json.loads(m.group(0))
            else:
                # Last resort: single-task fallback
                task_data = {
                    "original_prompt": prompt,
                    "tasks": [
                        {"id": 1, "priority": 1, "title": "Execute user request",
                         "description": prompt, "status": "pending"}
                    ]
                }

        # Write task file
        _save_tasks(task_data)

        # Return a concise objective summary for loop status displays
        task_count = len(task_data.get("tasks", []))
        return f"TASK_FILE:{TASK_FILE} ({task_count} tasks for: {prompt[:80]})"


# ── 2. Planner ─────────────────────────────────────────────────────────────────

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

    def _build_task_prompt(self, task: dict, previous_results: str = "",
                           file_contents: dict = None) -> str:
        tool_info = json.dumps(self.tools.get_all_tools_info(), indent=2)
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

    async def stream_thinking(self, objective: str, previous_results: str = ""):
        """Show which task we are currently executing."""
        # objective here is a task title injected by AshbornLoop
        thinking_prompt = (
            f"You are ASHBORN. In 1-2 sentences, describe what you are about to do for this task:\n"
            f"Task: {objective}\n"
            f"Focus on WHAT tool you will use and WHY."
        )
        try:
            stream_fn = getattr(self.llm, "generate_stream", None)
            if callable(stream_fn):
                stream = stream_fn(thinking_prompt, session_id=None, max_tokens=120)
                if hasattr(stream, "__aiter__"):
                    async for chunk in stream:
                        yield chunk
                    return
            text = await self.llm.generate(thinking_prompt, session_id=None, max_tokens=120)
            for word in (text or "").split():
                yield word + " "
        except Exception:
            yield f"Executing: {objective}"

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


# ── 3. Reflector ────────────────────────────────────────────────────────────────

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

    async def reflect(self, objective: str, action: dict, result: str) -> dict:
        prompt = f"""{self.SYSTEM_INSTRUCTION}

Task Description: {objective}
Action Taken    : {json.dumps(action)}
Tool Result     : {result}

JSON Response:
"""
        response = await self.llm.generate(prompt, session_id=None)
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


# ── 4. AshbornLoop ─────────────────────────────────────────────────────────────

class AshbornLoop(AgentLoop):
    """
    Task-file driven agent loop:
      - Reads .ashborn_tasks.json generated by AshbornThinker
      - Executes tasks sorted by priority
      - Marks each task done/failed in the file
      - Deletes the file after all tasks are processed
    """

    MAX_RETRIES_PER_TASK = 2
    MAX_TOTAL_ACTIONS = 30

    def _schedule_background(self, coro):
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)

        def _on_done(t):
            self._background_tasks.discard(t)
            try:
                _ = t.exception()
            except Exception:
                pass

        task.add_done_callback(_on_done)

    def _get_pending_tasks(self) -> list:
        """Load and return tasks sorted by priority that are still pending."""
        try:
            data = _load_tasks()
            return sorted(
                [t for t in data["tasks"] if t["status"] == "pending"],
                key=lambda t: t.get("priority", 99)
            )
        except Exception:
            return []

    def _has_task_file(self) -> bool:
        return os.path.exists(TASK_FILE)

    async def run(self, prompt: str, memory, session_id: str, max_iterations: int = 5) -> str:
        # Step 1: Think — generates .ashborn_tasks.json
        objective_meta = await self.thinker.analyze(prompt, memory, session_id)
        memory.session.set("current_objective", objective_meta)

        # Step 2: Analyze workspace concurrently (best-effort)
        try:
            analysis = await self.analyzer.analyze_workspace(prompt)
            memory.session.set("project_analysis", analysis)
        except Exception:
            pass

        await memory.add_interaction(session_id, "system", f"Task breakdown: {objective_meta}")

        accumulated_results = ""
        task_summaries = []
        total_actions = 0

        # Step 3: Execute tasks by priority
        while self._has_task_file() and total_actions < self.MAX_TOTAL_ACTIONS:
            pending = self._get_pending_tasks()
            if not pending:
                break

            task = pending[0]

            for attempt in range(self.MAX_RETRIES_PER_TASK):
                plan = await self.planner.plan_task(task, accumulated_results)
                actions = plan.get("actions", [])

                # Skip if planner says finish for this task
                if any(a.get("tool") == "finish" for a in actions):
                    _mark_task(task["id"], "done")
                    task_summaries.append(f"✓ [{task['priority']}] {task['title']}: skipped (already done)")
                    break

                action_result = await self.actor.execute(plan)
                total_actions += len([a for a in actions if a.get("tool") != "finish"])

                reflection = await self.reflector.reflect(task["description"], plan, action_result)

                accumulated_results += (
                    f"\nTask '{task['title']}' (attempt {attempt + 1}):\n"
                    f"  Result: {action_result}\n"
                    f"  Reflection: {reflection['reflection']}\n"
                )

                self._schedule_background(memory.add_interaction(
                    session_id, "system",
                    f"Task: {task['title']} | Result: {action_result} | Reflection: {reflection['reflection']}"
                ))

                if reflection["is_complete"]:
                    _mark_task(task["id"], "done")
                    task_summaries.append(f"✓ [{task['priority']}] {task['title']}")
                    break
                elif attempt == self.MAX_RETRIES_PER_TASK - 1:
                    _mark_task(task["id"], "failed")
                    task_summaries.append(f"✗ [{task['priority']}] {task['title']}: failed after {self.MAX_RETRIES_PER_TASK} attempts")

        # Step 4: Cleanup
        if self._has_task_file():
            try:
                os.remove(TASK_FILE)
            except Exception:
                pass

        # Step 5: Synthesize final answer
        summary = "\n".join(task_summaries) if task_summaries else "No tasks were executed."
        final_answer = f"**Ashborn Task Execution Complete**\n\n{summary}\n\n---\n{accumulated_results.strip()}"
        await memory.add_interaction(session_id, "assistant", final_answer)
        return final_answer

    async def run_stream(self, prompt: str, memory, session_id: str, max_iterations: int = 5):
        # Step 1: Think
        yield {"type": "status", "content": "🧠 Decomposing your request into tasks..."}
        objective_meta = await self.thinker.analyze(prompt, memory, session_id)
        memory.session.set("current_objective", objective_meta)

        # Extract task count from meta string for display
        task_count_str = ""
        if "(" in objective_meta:
            task_count_str = objective_meta.split("(")[1].split(")")[0]

        yield {"type": "status", "content": f"📋 Task file created — {task_count_str}"}

        # Analyze workspace best-effort
        try:
            analysis = await self.analyzer.analyze_workspace(prompt)
            memory.session.set("project_analysis", analysis)
        except Exception:
            pass

        await memory.add_interaction(session_id, "system", f"Task breakdown: {objective_meta}")

        accumulated_results = ""
        task_summaries = []
        total_actions = 0
        task_number = 0

        # Step 3: Execute tasks by priority
        while self._has_task_file() and total_actions < self.MAX_TOTAL_ACTIONS:
            pending = self._get_pending_tasks()
            if not pending:
                break

            task = pending[0]
            task_number += 1

            # Count total for display
            try:
                all_tasks_count = len(_load_tasks().get("tasks", []))
            except Exception:
                all_tasks_count = "?"

            yield {
                "type": "status",
                "content": f"⚙ Task {task_number}/{all_tasks_count} [P{task['priority']}]: {task['title']}"
            }

            # Stream planner thinking for this task
            yield {"type": "chunk", "content": f"\n**[P{task['priority']}] {task['title']}**\n"}
            async for thought in self.planner.stream_thinking(task["description"], accumulated_results):
                yield {"type": "chunk", "content": thought}
            yield {"type": "chunk", "content": "\n"}

            for attempt in range(self.MAX_RETRIES_PER_TASK):
                plan = await self.planner.plan_task(task, accumulated_results)
                actions = plan.get("actions", [])

                if any(a.get("tool") == "finish" for a in actions):
                    _mark_task(task["id"], "done")
                    task_summaries.append(f"✓ {task['title']}")
                    yield {"type": "chunk", "content": f"  ↳ Skipped (already complete)\n"}
                    break

                yield {"type": "status", "content": f"  Executing {len(actions)} action(s)..."}
                action_result = await self.actor.execute(plan)
                total_actions += len([a for a in actions if a.get("tool") != "finish"])

                reflection = await self.reflector.reflect(task["description"], plan, action_result)

                accumulated_results += (
                    f"\nTask '{task['title']}' (attempt {attempt + 1}):\n"
                    f"  Result: {action_result}\n"
                    f"  Reflection: {reflection['reflection']}\n"
                )

                self._schedule_background(memory.add_interaction(
                    session_id, "system",
                    f"Task: {task['title']} | Result: {action_result} | Reflection: {reflection['reflection']}"
                ))

                if reflection["is_complete"]:
                    _mark_task(task["id"], "done")
                    task_summaries.append(f"✓ {task['title']}")
                    yield {"type": "chunk", "content": f"  ↳ ✓ Done: {reflection['reflection']}\n"}
                    break
                else:
                    if attempt < self.MAX_RETRIES_PER_TASK - 1:
                        yield {"type": "chunk", "content": f"  ↳ ⚠ Retrying: {reflection['reflection']}\n"}
                    else:
                        _mark_task(task["id"], "failed")
                        task_summaries.append(f"✗ {task['title']}")
                        yield {"type": "chunk", "content": f"  ↳ ✗ Failed: {reflection['reflection']}\n"}

        # Step 4: Cleanup
        if self._has_task_file():
            yield {"type": "status", "content": "🗑 Cleaning up task file..."}
            try:
                os.remove(TASK_FILE)
            except Exception:
                pass

        # Step 5: Final summary
        summary_lines = "\n".join(task_summaries) if task_summaries else "No tasks were executed."
        yield {"type": "chunk", "content": f"\n\n---\n**All tasks complete!**\n\n{summary_lines}\n"}

        final_answer = f"Tasks complete:\n{summary_lines}\n\n{accumulated_results.strip()}"
        await memory.add_interaction(session_id, "assistant", final_answer)
