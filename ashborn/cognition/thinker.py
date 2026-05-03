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

=== STRICT DIRECTIVES ===
1. Respond ONLY with valid JSON.
2. No conversational filler, preambles, or post-commentary.
3. Each task must be ATOMIC (one clear action).
4. For the "type" field, use EXACTLY one of: new_file | modify_file | command | read.
5. "priority" starts at 1 (earliest).

User Request:
{prompt}

Context:
{context}

=== RESPONSE SCHEMA ===
{{
    "original_prompt": "<user request>",
    "tasks": [
        {{
            "id": 1,
            "priority": 1,
            "type": "new_file | modify_file | command | read",
            "title": "<short title>",
            "description": "<detailed implementation instruction>",
            "dependencies": [],
            "status": "pending"
        }}
    ]
}}
"""

    async def analyze(self, prompt: str, memory, session_id: str) -> str:
        from .helpers.schemas import validate_schema, TASK_SCHEMA
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
            # Fallback block detection
            m = re.search(r'\{.*\}', clean, re.DOTALL)
            if m:
                try: task_data = json.loads(m.group(0))
                except: task_data = None
            else:
                task_data = None
        
        if not task_data:
            # Final fallback
            task_data = {
                "original_prompt": prompt,
                "tasks": [{"id": 1, "priority": 1, "title": "Execute user request", "description": prompt, "status": "pending", "type": "command"}]
            }

        # Schema Validation
        errors = validate_schema(task_data, TASK_SCHEMA)
        if errors:
            print(f"[THINKER WARNING] Schema validation failed: {errors}")
            # We could try to fix it, but for now we just log it.

        # Write task file
        _save_tasks(task_data)

        # Return a concise objective summary for loop status displays
        task_count = len(task_data.get("tasks", []))
        return f"TASK_FILE:{TASK_FILE} ({task_count} tasks for: {prompt[:80]})"
