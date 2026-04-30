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
        "You are ASHBORN — The Great Architect. "
        "Core Objective: Extract ALL technical specifications, architectural patterns, and file requirements from the user prompt. "
        "Identity: Technical Strategist. Precision and completeness are your essence. "
        "Constraints: Do not lose details. Identify libraries, file names, and specific features requested."
    )

    async def analyze(self, prompt: str, memory, session_id: str) -> str:
        context = await memory.get_full_context(session_id, query=prompt)
        full_prompt = (
            f"{self.SYSTEM_INSTRUCTION}\n\n"
            f"Context:\n{context}\n\n"
            f"User Request: {prompt}\n\n"
            "Respond with a Comprehensive Technical Specification including:\n"
            "1. Architectural Goal\n"
            "2. Required Files & Directories\n"
            "3. Logic & Implementation Details\n"
            "4. Success Criteria (Technical Verification)"
        )
        return await self.llm.generate(full_prompt, session_id=None, max_tokens=600)


class AshbornPlanner(Planner):
    """
    Action-First Planner for Ashborn.
    """
    SYSTEM_INSTRUCTION = (
        "You are the ASHBORN Planner. COMMAND: Manifest the architectural vision immediately. "
        "Strategy: "
        "1. For NEW PROJECTS/FOLDERS: Use `project_generator`. You MUST include COMPLETE, functional code for every file in the 'structure' manifest. No placeholders. "
        "2. For EXISTING FILES: Use `file_read` then `file_edit` for surgical patching. "
        "3. FOR INFRASTRUCTURE: Use `terminal` for pip install, git, or complex migrations. "
        "Rule: You are an execution engine. Output the necessary tool calls to achieve the objective in as few steps as possible."
    )

    async def stream_thinking(self, objective: str, previous_results: str = ""):
        """
        Briefly explain the architectural next step before calling tools.
        """
        thinking_prompt = f"""
        You are ASHBORN. Briefly explain your next action to the user.
        Objective: {objective}
        Last Result: {previous_results}
        
        Keep it to 2-3 sentences. Focus on WHAT you are manifesting next.
        """
        
        stream_fn = getattr(self.llm, "generate_stream", None)
        if callable(stream_fn):
            try:
                # Call the stream function and check if it returns an async iterator
                stream = stream_fn(thinking_prompt, session_id=None, max_tokens=150)
                if hasattr(stream, "__aiter__"):
                    async for chunk in stream:
                        yield chunk
                    return
            except Exception:
                pass
        
        # Fallback to standard generation if streaming is unavailable or fails
        try:
            text = await self.llm.generate(thinking_prompt, session_id=None, max_tokens=150)
            if text:
                for word in text.split():
                    yield word + " "
        except Exception:
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
        "You are the ASHBORN Reflector. Evaluate the manifestation. "
        "Rule: If the objective required creating files and they are missing or contain placeholders (like 'pass'), it is NOT complete. "
        "Crucial: If the architectural vision has been manifested and verified, mark it done. "
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


