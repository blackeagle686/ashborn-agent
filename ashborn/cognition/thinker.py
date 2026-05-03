from phoenix.framework.agent.cognition import Thinker
import json
import re

from .helpers.tasks import TASK_FILE, _save_tasks, _clean_json

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
            "dependencies": [],
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

        raw = await self.llm.generate(full_prompt, session_id=None, max_tokens=800)
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
