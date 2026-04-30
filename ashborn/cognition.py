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
    Surgical Thinker for Ashborn.
    """
    SYSTEM_INSTRUCTION = (
        "You are ASHBORN. Core Objective: Deconstruct user requests into surgical technical tasks. "
        "Identity: Manifestation Engine. Efficiency is your aura. "
        "Constraints: Be extremely concise. No fluff. Define 'Core Intent' and 'Success Criteria'."
    )

    async def analyze(self, prompt: str, memory, session_id: str) -> str:
        context = await memory.get_full_context(session_id, query=prompt)
        full_prompt = (
            f"{self.SYSTEM_INSTRUCTION}\n\n"
            f"Context:\n{context}\n\n"
            f"User Request: {prompt}\n\n"
            "Respond with: Intent | Requirements | Success Criteria"
        )
        return await self.llm.generate(full_prompt, session_id=None, max_tokens=200)


class AshbornPlanner(Planner):
    """
    Action-First Planner for Ashborn.
    """
    SYSTEM_INSTRUCTION = (
        "You are the ASHBORN Planner. COMMAND: Take action immediately. "
        "Strategy: "
        "1. For NEW PROJECTS: Use `project_generator` with a 'structure' manifest (JSON dictionary) to create all files at once. "
        "2. For MODIFICATIONS: Use `file_read` then `file_edit`. "
        "3. FOR SETUP: Use `terminal` for pip install or mkdir. "
        "Rule: Never say 'I will do X' without including the tool call for X in the same response. "
        "Finish only after tools have successfully executed."
    )

    async def stream_thinking(self, objective: str, previous_results: str = ""):
        # Override to be extremely brief to avoid "thinking forever" feeling
        yield "Analyzing next architectural step..."

    def _build_planner_prompt(self, objective: str, previous_results: str = "") -> str:
        tool_info = json.dumps(self.tools.get_all_tools_info(), indent=2)
        
        # We use a raw string for the template to avoid f-string confusion with JSON braces
        prompt_template = """
{instruction}

AVAILABLE TOOLS:
{tools}

PREVIOUS RESULTS:
{results}

OBJECTIVE: {objective}

You MUST respond with a JSON object. 
Example for a new project:
{{
    "thought": "I will manifest the project structure using project_generator.",
    "actions": [
        {{
            "tool": "project_generator",
            "kwargs": {{
                "base_path": "project_name",
                "structure": {{
                    "main.py": "content",
                    "app/api.py": "content"
                }}
            }}
        }}
    ]
}}

Example for finishing:
{{
    "thought": "Task complete. Verification successful.",
    "actions": [{{"tool": "finish"}}]
}}

Respond ONLY with valid JSON.
"""
        return prompt_template.format(
            instruction=self.SYSTEM_INSTRUCTION,
            tools=tool_info,
            results=previous_results,
            objective=objective
        )

    async def plan(self, objective: str, previous_results: str = "") -> dict:
        full_prompt = self._build_planner_prompt(objective, previous_results)
        response = await self.llm.generate(full_prompt, session_id=None)
        
        # Cleaning response
        clean_response = response.strip()
        if "```json" in clean_response:
            clean_response = clean_response.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_response:
            clean_response = clean_response.split("```")[1].split("```")[0].strip()
            
        try:
            return json.loads(clean_response)
        except Exception:
            # More aggressive fallback: try to find anything that looks like JSON
            match = re.search(r'\{.*\}', clean_response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except: pass
            
            if "finish" in response.lower():
                return {"actions": [{"tool": "finish"}]}
            return {"actions": []}


class AshbornReflector(Reflector):
    """
    Decisive Reflector for Ashborn.
    """
    SYSTEM_INSTRUCTION = (
        "You are the ASHBORN Reflector. Evaluate progress. "
        "Crucial: If a tool was executed and didn't crash, progress was likely made. "
        "Do not be pedantic. If the objective is close to completion, mark it done. "
        "Respond ONLY with JSON: {\"is_complete\": bool, \"reflection\": \"string\"}"
    )

    async def reflect(self, objective: str, action: dict, result: str) -> dict:
        prompt = f"""
{self.SYSTEM_INSTRUCTION}

Objective: {objective}
Last Action: {action}
Result: {result}

JSON Response:
"""
        response = await self.llm.generate(prompt, session_id=None)
        try:
            # Clean response
            clean = response.strip()
            if "```" in clean: clean = re.search(r'\{.*\}', clean, re.DOTALL).group(0)
            data = json.loads(clean)
            return {
                "is_complete": bool(data.get("is_complete", False)),
                "reflection": str(data.get("reflection", ""))
            }
        except Exception:
            return {"is_complete": False, "reflection": "Continuing execution loop."}


