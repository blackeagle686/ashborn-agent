"""
Ashborn Agent — Main launcher.
Boots the Textual TUI, routing to the setup wizard when config is missing,
or directly to the full-screen chat interface otherwise.
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from textual.app import App, ComposeResult
from .cli.theme import ASHBORN_THEME
from .cli.splash_screen import SplashScreen


# ── Configuration Path ────────────────────────────────────────────────────────
# Default to local .env, fallback to ~/.ashborn/.env for global use
ENV_PATH = Path(".env")
GLOBAL_CONFIG_DIR = Path.home() / ".ashborn"
GLOBAL_ENV_PATH = GLOBAL_CONFIG_DIR / ".env"


def _has_valid_config() -> bool:
    """Return True if any .env has a non-empty API key."""
    # Check local first, then global
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
    elif GLOBAL_ENV_PATH.exists():
        load_dotenv(GLOBAL_ENV_PATH, override=True)
    
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
            from .cli.chat_screen import ChatScreen
            self.push_screen(ChatScreen())
        else:
            from .cli.setup_wizard import SetupWizard
            self.push_screen(SetupWizard())
        
        # Show splash on top of the initial screen
        self.push_screen(SplashScreen())


def main() -> None:
    """Entry point — handles 'ashborn <dir>'."""
    # ── Silence noisy startup logs ─────────────────────────────────────────────
    os.environ.setdefault("LOG_LEVEL", "WARNING")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

    # Handle directory argument (e.g. 'ashborn .')
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1])
        if target_dir.is_dir():
            print(f"[*] Switching to directory: {target_dir.absolute()}")
            os.chdir(target_dir)
        else:
            print(f"[!] Error: {target_dir} is not a valid directory.")
            sys.exit(1)

    app = AshbornApp()
    app.run()


if __name__ == "__main__":
    main()
