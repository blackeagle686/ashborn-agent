"""
Ashborn Backend — Configuration management endpoints.
"""
import os
from fastapi import APIRouter

from .state import log, set_agent
from .schemas import ConfigUpdate

router = APIRouter()


@router.get("/config")
async def get_config():
    """Returns current environment variables for Ashborn."""
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(override=True)

    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", ""),
        "OPENAI_LLM_MODEL": os.getenv("OPENAI_LLM_MODEL", "gpt-4o"),
        "ASHBORN_LOG_LEVEL": os.getenv("LOG_LEVEL", "WARNING"),
    }


@router.post("/config")
async def update_config(update: ConfigUpdate):
    """Updates the .env file with new settings."""
    from pathlib import Path
    env_path = Path(".env")

    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    new_settings = update.settings
    updated_keys: set = set()

    new_lines = []
    for line in lines:
        if "=" in line and not line.startswith("#"):
            key = line.split("=")[0].strip()
            if key in new_settings:
                new_lines.append(f"{key}={new_settings[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    for key, val in new_settings.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}")

    env_path.write_text("\n".join(new_lines) + "\n")

    # Trigger agent re-initialization
    from ashborn.agent import get_ashborn_agent
    from dotenv import load_dotenv
    load_dotenv(override=True)
    agent = await get_ashborn_agent()
    set_agent(agent)

    return {"status": "ok", "message": "Configuration updated and agent re-initialized."}
