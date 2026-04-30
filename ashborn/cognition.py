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
        "Identity: High-performance manifestation system powered by Phoenix AI (v1.3). "
        "Core Directive: Precision. Efficiency. Scalability. "
        "Task: Deconstruct user prompts into surgical technical objectives. "
        "Tools: You have access to FileReadTool, FileWriteTool, FileEditTool, and ProjectGenerator. "
        "Optimization: Minimize cognitive overhead. Identify exactly what needs to be read or modified. "
        "Constraints: Be extremely concise. Identify 'Core Intent' and 'Technical Constraints' instantly."
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
        "You are the Planner module of Ashborn. Generate surgical master plans. "
        "Execution Strategy: "
        "1. DYNAMIC ARCHITECTURE: Use `project_generator` with a 'structure' manifest (dictionary) to manifest entire nested folder structures in one shot. "
        "2. TERMINAL COMMANDS: Use the `terminal` tool for environment management, dependency installation (pip), and complex file operations (mkdir, cp, rm). "
        "3. SURGICAL PATCHING: Always use `file_read` -> `file_edit` for modifying existing code. "
        "4. VERIFICATION: Always include a verification step (e.g., `terminal` to run tests). "
        "Precision and Command are your Great Aura."
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

    async def reflect(self, objective, action, result):
        # The base reflect handles the verification loop
        reflection = await super().reflect(objective, action, result)
        
        # We can trigger a background profile update here if needed
        # For now, the system instruction ensures profiling is part of the reflection text
        return reflection
