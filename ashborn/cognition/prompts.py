"""
Ashborn Prompts — centralised prompt templates for the cognition loop.
"""

FAST_ANSWER_SYSTEM = "You are ASHBORN. Give a concise, direct answer to the user's question."


def build_fast_answer_prompt(context: str, user_prompt: str) -> str:
    """Compose the full prompt for fast-answer mode."""
    return f"{FAST_ANSWER_SYSTEM}\n\nContext:\n{context}\n\nUser: {user_prompt}"
