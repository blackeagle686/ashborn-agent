from phoenix.framework.agent.cognition import Planner
import json
import re

from .helpers.tasks import _clean_json
from .helpers.plan import _load_plan, _save_plan

class AshbornPlanner(Planner):
    """
    Receives one task at a time and generates a sequence of plan_steps (analysis, design, implementation, validation).
    It persists these to ashborn.plan.json and does NOT generate tool actions directly.
    """

    PLAN_GENERATION_PROMPT = """\
You are the ASHBORN Planning Engine. You receive ONE task and must break it down into logical execution steps.
These steps should outline HOW to accomplish the task before any code is generated or tools are executed.

Your output MUST be a JSON object containing "plan_steps" array.
Each plan step must follow this schema exactly:
{{
  "plan_steps": [
    {{
      "plan_step_id": <INT>,
      "task_id": <INT>,
      "step_index": <INT>,
      "type": "<analysis | design | implementation | validation>",
      "solution": {{
        "approach": "<detailed text explanation of what this step accomplishes>",
        "algorithm": "<optional details of algorithms/logic used>",
        "complexity": "<optional>"
      }},
      "dependencies": [<INT> (list of plan_step_id this step depends on)],
      "status": "pending"
    }}
  ]
}}

Task Info:
Task ID: {task_id}
Priority: {priority}
Title: {title}
Description: {description}

Respond ONLY with valid JSON.
"""

    async def generate_plan_steps(self, task: dict) -> list:
        """
        Ask LLM to generate plan steps for the given task and persist to ashborn.plan.json.
        """
        prompt = self.PLAN_GENERATION_PROMPT.format(
            task_id=task.get("id", 1),
            priority=task.get("priority", 1),
            title=task.get("title", ""),
            description=task.get("description", "")
        )

        response = await self.llm.generate(prompt, session_id=None)
        clean = _clean_json(response)
        
        try:
            plan_data = json.loads(clean)
        except Exception:
            m = re.search(r'\{.*\}', clean, re.DOTALL)
            if m:
                plan_data = json.loads(m.group(0))
            else:
                plan_data = {"plan_steps": []}
                
        new_steps = plan_data.get("plan_steps", [])
        
        # Automatically assign unique integer plan_step_ids
        existing_plan = _load_plan()
        existing_steps = existing_plan.get("plan_steps", [])
        
        next_step_id = 1
        if existing_steps:
            next_step_id = max((s.get("plan_step_id", 0) for s in existing_steps)) + 1
            
        for step in new_steps:
            # Force task_id to match the current task
            step["task_id"] = task.get("id", 1)
            # Re-assign IDs to prevent collisions
            step["plan_step_id"] = next_step_id
            step["status"] = "pending"
            next_step_id += 1
            
        existing_steps.extend(new_steps)
        existing_plan["plan_steps"] = existing_steps
        _save_plan(existing_plan)
        
        return new_steps

    def task_status_line(self, task: dict) -> str:
        """Return a deterministic status line from the task dict — no LLM call needed."""
        type_icon = {"new_file": "📄", "modify_file": "✏️", "command": "⚡", "read": "🔍"}
        icon = type_icon.get(task.get("type", ""), "⚙")
        return f"{icon} {task.get('description', task.get('title', ''))[:120]}"

    async def plan(self, objective: str, previous_results: str = "") -> dict:
        """Fallback if called directly by generic agents. Not typically used in AshbornLoop."""
        return {"actions": [{"tool": "finish"}]}
