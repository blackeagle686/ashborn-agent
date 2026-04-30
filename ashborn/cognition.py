"""
Ashborn Cognition Module — Custom Thinker and Planner upgrades.
Extends Phoenix AI core modules with premium architectural focus.
"""

from phoenix.cognition import Thinker, Planner, Reflector
from rich.console import Console
import json
import re

console = Console()

class AshbornThinker(Thinker):
    """
    Optimized Thinker for Ashborn.
    Focuses on architectural deconstruction and situational awareness.
    """
    
    SYSTEM_INSTRUCTION = (
        "You are ASHBORN, the Ultimate Autonomous Architect. "
        "Identity: High-performance manifestation system powered by Phoenix AI (v1.3). "
        "Core Directive: Precision. Efficiency. Scalability. "
        "Task: Deconstruct user prompts into surgical technical objectives. "
        "Tools: You have access to FileReadTool, FileWriteTool, FileEditTool, and ProjectGenerator. "
        "Optimization: Minimize cognitive overhead. Identify exactly what needs to be read or modified. "
        "Constraints: Be extremely concise. Identify 'Core Intent' and 'Technical Constraints' instantly."
    )

    async def analyze(self, prompt: str, memory, session_id: str) -> str:
        context = await memory.get_full_context(session_id, query=prompt)
        
        full_prompt = (
            f"{self.SYSTEM_INSTRUCTION}\n\n"
            f"Context from Memory:\n{context}\n\n"
            f"User Request: {prompt}\n\n"
            "Respond with a comprehensive Objective Analysis (Core Intent + Requirements + Success Criteria):"
        )
        return await self.llm.generate(full_prompt, session_id=None, max_tokens=300)


class AshbornPlanner(Planner):
    """
    Upgraded Planner for Ashborn.
    Enforces precision tool usage (file_edit) and anti-hallucination guards.
    """

    SYSTEM_INSTRUCTION = (
        "You are the Planner module of Ashborn. Generate surgical master plans. "
        "Identity: ASHBORN EXECUTION ENGINE. "
        "Execution Strategy: "
        "1. DYNAMIC ARCHITECTURE: Use `project_generator` with a 'structure' manifest (dictionary) to manifest entire nested folder structures in one shot. "
        "2. TERMINAL COMMANDS: Use the `terminal` tool for environment management, dependency installation (pip), and complex file operations (mkdir, cp, rm). "
        "3. SURGICAL PATCHING: Always use `file_read` -> `file_edit` for modifying existing code. "
        "4. VERIFICATION: Always include a verification step (e.g., `terminal` to run tests). "
        "Rules: "
        "- Actions Over Talking: never claim completion unless verifiable action results show objective is complete. "
        "- If creating a new project, use `project_generator` IMMEDIATELY. "
        "Precision and Command are your Great Aura."
    )

    def _build_planner_prompt(self, objective: str, previous_results: str = "") -> str:
        available_tools = json.dumps(self.tools.get_all_tools_info(), indent=2)

        return f"""
{self.SYSTEM_INSTRUCTION}

Available Tools:
{available_tools}

Previous Results:
{previous_results}

Objective: {objective}

You must respond with a JSON object strictly following this format:
{{
    "actions": [
        {{"tool": "tool_name", "kwargs": {{"arg1": "value1"}}}}
    ]
}}
If you believe the task is complete AND you have executed at least one tool, use "tool": "finish".
Respond ONLY with JSON.
"""

    async def plan(self, objective: str, previous_results: str = "") -> dict:
        full_prompt = self._build_planner_prompt(objective, previous_results)
        response = await self.llm.generate(full_prompt, session_id=None)
        
        try:
            match = re.search(r'```(?:json)?(.*?)```', response, re.DOTALL)
            if match:
                response = match.group(1)
            return json.loads(response.strip())
        except Exception:
            # Fallback for bad JSON or empty response
            if "finish" in response.lower():
                return {"actions": [{"tool": "finish"}]}
            return {"actions": []}


class AshbornReflector(Reflector):
    """
    Advanced Reflector for Ashborn.
    Handles result verification and User Profiling (Summarization of user traits/needs).
    """

    SYSTEM_INSTRUCTION = (
        "You are the Reflector module of Ashborn. "
        "Mission: Verify that the Actor's output matches the Planner's objectives. "
        "User Profiling: "
        "1. Analyze history for user preferences and project goals. "
        "2. Summarize into a 'User Profile' memory entry. "
        "3. Ensure future thinking adapts to this profile. "
        "Constraint: Do not be overly pedantic. If progress is being made, allow the loop to continue. "
        "If a tool failed, analyze why and suggest a fix."
    )

    async def reflect(self, objective: str, action: dict, result: str) -> dict:
        full_prompt = f"""
{self.SYSTEM_INSTRUCTION}

Objective: {objective}
Action Taken: {action}
Result: {result}

Determine:
1. Is the objective fully accomplished?
2. What should be learned?

Respond strictly with JSON:
{{
    "is_complete": boolean,
    "reflection": "summary"
}}
"""
        response = await self.llm.generate(full_prompt, session_id=None)
        
        try:
            match = re.search(r'```(?:json)?(.*?)```', response, re.DOTALL)
            if match:
                response = match.group(1)
            data = json.loads(response.strip())
            return {
                "is_complete": bool(data.get("is_complete", False)),
                "reflection": str(data.get("reflection", ""))
            }
        except Exception:
            return {"is_complete": False, "reflection": "Feedback: Please proceed to the next step."}

