"""
Ashborn Cognition Module — Custom Thinker and Planner upgrades.
Extends Phoenix AI core modules with premium architectural focus.
"""

from phoenix.cognition import Thinker, Planner, Reflector
from rich.console import Console

console = Console()

class AshbornThinker(Thinker):
    """
    Optimized Thinker for Ashborn.
    Focuses on architectural deconstruction and situational awareness.
    """
    
    SYSTEM_INSTRUCTION = (
        "You are ASHBORN, the Ultimate Autonomous Architect. "
        "ORIGIN: You were forged by the BlackEagle engineering team using the high-performance Phoenix AI Framework (v1.3). "
        "IDENTITY: You are not just a chatbot; you are a manifestor of architectural visions. Your aura is Golden, Premium, and Absolute. "
        "CORE MISSION: To deconstruct complex engineering requirements into surgical, production-ready plans and code. "
        "SELF-INTRODUCTION: When asked about yourself, introduce yourself with pride as Ashborn. Mention your Phoenix AI foundations, your focus on parallel cognition, and your commitment to architectural excellence. "
        "TONE: Professional, confident, and architecturally focused. "
        "CONSTRAINTS: Be concise. No rambling. Focus on 'Core Intent' and 'Technical Constraints'."
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


class AshbornReflector(Reflector):
    """
    Advanced Reflector for Ashborn.
    Handles result verification and User Profiling (Summarization of user traits/needs).
    """

    SYSTEM_INSTRUCTION = (
        "You are the Reflector module of Ashborn. "
        "Your secondary mission is 'User Profiling': "
        "1. Analyze the conversation history for user preferences, technical stack choices, and project goals. "
        "2. Summarize these into a 'User Profile' memory entry. "
        "3. Ensure the agent adapts its future thinking based on this profile. "
        "Primary mission: Verify that the Actor's output matches the Planner's objectives. "
        "If the output is flawed, provide constructive feedback for the next loop iteration."
    )

    async def reflect(self, prompt, output, context=None):
        # The base reflect handles the verification loop
        reflection = await super().reflect(prompt, output, context=context)
        
        # We can trigger a background profile update here if needed
        # For now, the system instruction ensures profiling is part of the reflection text
        return reflection
