"""
Ashborn Agent — Main launcher.
Boots the Textual TUI, routing to the setup wizard when config is missing,
or directly to the full-screen chat interface otherwise.
"""

import os
import re
from pathlib import Path

# ── Silence noisy startup logs BEFORE any phoenix imports ─────────────────────
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

from dotenv import load_dotenv
from textual.app import App, ComposeResult

from cli.theme import ASHBORN_THEME


ENV_PATH = Path(".env")


def _has_valid_config() -> bool:
    """Return True if .env has a non-empty API key."""
    load_dotenv(override=True)
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return bool(key)


class AshbornApp(App):
    """Root Textual application for the Ashborn Agent CLI."""

    TITLE = "Ashborn Agent"
    SUB_TITLE = "Powered by Phoenix AI"
    CSS = ""                        # All CSS lives inside screens
    ENABLE_COMMAND_PALETTE = False  # Keep UI clean

    def on_mount(self) -> None:
        # Apply the custom theme
        self.register_theme(ASHBORN_THEME)
        self.theme = "ashborn"

        if _has_valid_config():
            from cli.chat_screen import ChatScreen
            self.push_screen(ChatScreen())
        else:
            from cli.setup_wizard import SetupWizard
            self.push_screen(SetupWizard())


def main() -> None:
    """Entry point — can be called from scripts or `python main.py`."""
    app = AshbornApp()
    app.run()


if __name__ == "__main__":
    main()
