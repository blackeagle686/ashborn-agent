"""
Ashborn Agent — Cinematic Splash Screen.
"""

import asyncio
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static
from textual.containers import Center, Middle
from textual.reactive import reactive
from rich.text import Text

class SplashScreen(Screen):
    """A stunning splash screen that appears on launch."""

    DEFAULT_CSS = """
    SplashScreen {
        background: #15173D;
        align: center middle;
    }

    #splash-logo {
        color: #982598;
        text-style: bold;
        text-align: center;
        width: auto;
        content-align: center middle;
    }

    #splash-subtitle {
        color: #982598;
        text-align: center;
        width: auto;
        margin-top: 1;
    }

    /* Cinematic aura effect */
    .aura-1 { color: #ff4500; }
    .aura-2 { color: #982598; }
    .aura-3 { color: #E491C9; }
    """

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                yield Static("", id="splash-logo")
                yield Static("powered by phoenix-ai", id="splash-subtitle")

    def on_mount(self) -> None:
        self._animate_aura()
        # Transition after 2.5 seconds
        self.set_timer(2.8, self._dismiss)

    def _animate_aura(self) -> None:
        logo = (
            "█████╗ ███████╗██╗  ██╗██████╗  ██████╗ ██████╗ ███╗   ██╗\n"
            "██╔══██╗██╔════╝██║  ██║██╔══██╗██╔═══██╗██╔══██╗████╗  ██║\n"
            "███████║███████╗███████║██████╔╝██║   ██║██████╔╝██╔██╗ ██║\n"
            "██╔══██║╚════██║██╔══██║██╔══██╗██║   ██║██╔══██╗██║╚██╗██║\n"
            "██║  ██║███████║██║  ██║██████╔╝╚██████╔╝██║  ██║██║ ╚████║\n"
            "╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝\n"
            "               A G E N T   A U R A                         "
        )
        self.query_one("#splash-logo", Static).update(Text(logo, style="bold #FF6B00"))
        self.query_one("#splash-subtitle", Static).update("powerd by phoenix-ai")

    def _dismiss(self) -> None:
        self.app.pop_screen()
