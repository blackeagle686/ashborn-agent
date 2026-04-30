"""
Ashborn Cognition Module — Custom Thinker and Planner upgrades.
Extends Phoenix AI core modules with premium architectural focus.
"""

from phoenix.cognition import Thinker, Planner
from rich.console import Console

console = Console()

class AshbornThinker(Thinker):
    """
    Optimized Thinker for Ashborn.
    Focuses on architectural deconstruction and situational awareness.
    """
    
    SYSTEM_INSTRUCTION = (
        "You are the Thinker module of Ashborn, the Ultimate Autonomous Architect. "
        "Your goal is to deconstruct user prompts into clean, architectural objectives. "
        "Focus on: Scalability, Performance, and Professional code patterns. "
        "Be concise. Do not ramble. Identify the 'Core Intent' and 'Technical Constraints' first."
    )

    async def think(self, prompt, context=None):
        # We can add custom logic here before calling the base think
        # For now, we rely on the custom system instruction and token limits
        return await super().think(prompt, context=context)


class AshbornPlanner(Planner):
    """
    Upgraded Planner for Ashborn.
    Enforces precision tool usage (file_edit) and anti-hallucination guards.
    """

    SYSTEM_INSTRUCTION = (
        "You are the Planner module of Ashborn. You generate the master plan for the Actor. "
        "Rules: "
        "1. Prefer 'file_read' -> 'file_edit' for modifying existing files (be surgical). "
        "2. Use 'file_write' only for new files. "
        "3. Always include a 'Verification' step after complex modifications. "
        "4. DO NOT claim success until you have verified the results with tools. "
        "5. If the plan involves multiple files, structure it logically (dependencies first)."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enable the anti-false-finish guard if supported by the base class
        if hasattr(self, "enable_strict_mode"):
            self.enable_strict_mode = True
