"""
Ashborn Agent — Main Full-Screen Chat UI.

Layout:
  ┌─ Header ─────────────────────────────────────────────────────┐
  │ 🐦‍🔥 ASHBORN  │  model name  │  status badge                  │
  ├─ Body ──────────────────────────────────────────────────────┤
  │ Sidebar (collapsible) │  Chat window (scrollable messages)  │
  ├─ Input bar ──────────────────────────────────────────────────┤
  │ > prompt here...                              [nn chars]     │
  ├─ Footer ─────────────────────────────────────────────────────┤
  │  Enter: Send  Ctrl+L: Clear  Ctrl+K: Config  Ctrl+Q: Quit   │
  └──────────────────────────────────────────────────────────────┘
"""

import asyncio
from datetime import datetime
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Static, TextArea, RichLog,
    ContentSwitcher, TabbedContent, Label,
)
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.binding import Binding
from textual.reactive import reactive
from textual import on, work
from textual.worker import Worker, get_current_worker
from rich.text import Text
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.console import Console
from rich.segment import Segment

import os
from dotenv import load_dotenv


# ── Message data class ────────────────────────────────────────────────────────

class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role          # "user" | "assistant" | "system"
        self.content = content
        self.timestamp = datetime.now().strftime("%H:%M")


# ── Widgets ───────────────────────────────────────────────────────────────────

class SidebarWidget(Vertical):
    """Collapsible left sidebar showing session info & keyboard shortcuts."""

    DEFAULT_CSS = """
    SidebarWidget {
        width: 26;
        min-width: 26;
        background: #141414;
        border-right: tall #2a2a2a;
        padding: 1 1;
        display: block;
    }

    SidebarWidget.hidden {
        display: none;
    }

    .sidebar-title {
        color: #ff8c00;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    .sidebar-divider {
        color: #2a2a2a;
        width: 100%;
        margin-bottom: 1;
    }

    .sidebar-key-label {
        color: #666666;
        width: 100%;
        margin-bottom: 0;
    }

    .sidebar-key-val {
        color: #e0e0e0;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }

    .shortcut-row {
        color: #666666;
        width: 100%;
    }

    .shortcut-key {
        color: #00d4ff;
        text-style: bold;
    }
    """

    message_count: reactive[int] = reactive(0)
    token_estimate: reactive[int] = reactive(0)
    status: reactive[str] = reactive("● Ready")
    model_name: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("🐦‍🔥  ASHBORN", classes="sidebar-title")
        yield Static("─" * 22, classes="sidebar-divider")

        yield Static("Model", classes="sidebar-key-label")
        yield Static("", id="sb-model", classes="sidebar-key-val")

        yield Static("Status", classes="sidebar-key-label")
        yield Static("● Ready", id="sb-status", classes="sidebar-key-val")

        yield Static("Messages", classes="sidebar-key-label")
        yield Static("0", id="sb-msgs", classes="sidebar-key-val")

        yield Static("─" * 22, classes="sidebar-divider")
        yield Static("Shortcuts", classes="sidebar-title")
        yield Static("─" * 22, classes="sidebar-divider")

        shortcuts = [
            ("Enter",   "Send message"),
            ("Ctrl+L",  "Clear chat"),
            ("Ctrl+K",  "Config wizard"),
            ("Ctrl+B",  "Toggle sidebar"),
            ("Ctrl+Q",  "Quit"),
            ("Esc",     "Cancel stream"),
            ("↑/↓",     "Scroll history"),
        ]
        for key, desc in shortcuts:
            yield Static(f"[bold #00d4ff]{key:<9}[/] [#666666]{desc}[/]", classes="shortcut-row", markup=True)

    def watch_model_name(self, val: str) -> None:
        try:
            self.query_one("#sb-model", Static).update(val or "—")
        except Exception:
            pass

    def watch_status(self, val: str) -> None:
        try:
            self.query_one("#sb-status", Static).update(val)
        except Exception:
            pass

    def watch_message_count(self, val: int) -> None:
        try:
            self.query_one("#sb-msgs", Static).update(str(val))
        except Exception:
            pass


class ChatInputBar(Horizontal):
    """Bottom input bar with prompt prefix and char counter."""

    DEFAULT_CSS = """
    ChatInputBar {
        height: 5;
        background: #141414;
        border-top: tall #2a2a2a;
        padding: 0 1;
        align: left middle;
    }

    #input-prefix {
        color: #ff8c00;
        text-style: bold;
        width: auto;
        padding: 0 1;
        margin-top: 1;
    }

    #chat-input {
        background: #1a1a1a;
        border: tall #2a2a2a;
        color: #e0e0e0;
        width: 1fr;
        height: 3;
    }

    #chat-input:focus {
        border: tall #ff8c00;
        background: #1f1f1f;
    }

    #char-counter {
        color: #3a3a3a;
        width: auto;
        padding: 0 1;
        margin-top: 1;
    }

    #char-counter.warning {
        color: #ffd700;
    }

    #char-counter.danger {
        color: #ff4444;
    }
    """

    char_count: reactive[int] = reactive(0)
    MAX_CHARS = 4096

    def compose(self) -> ComposeResult:
        yield Static("❯", id="input-prefix")
        yield TextArea(id="chat-input", language=None)
        yield Static("0", id="char-counter")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        count = len(event.text_area.text)
        self.char_count = count
        counter = self.query_one("#char-counter", Static)
        counter.update(f"{count}")
        counter.remove_class("warning", "danger")
        if count > self.MAX_CHARS * 0.9:
            counter.add_class("danger")
        elif count > self.MAX_CHARS * 0.7:
            counter.add_class("warning")

    def get_text(self) -> str:
        return self.query_one("#chat-input", TextArea).text

    def clear(self) -> None:
        ta = self.query_one("#chat-input", TextArea)
        ta.load_text("")
        self.char_count = 0
        self.query_one("#char-counter", Static).update("0")

    def focus_input(self) -> None:
        self.query_one("#chat-input", TextArea).focus()


class ChatScreen(Screen):
    """Main full-screen interactive chat interface."""

    BINDINGS = [
        Binding("ctrl+q",     "quit_app",        "Quit",          show=False),
        Binding("ctrl+l",     "clear_chat",       "Clear",         show=False),
        Binding("ctrl+k",     "open_config",      "Config",        show=False),
        Binding("ctrl+b",     "toggle_sidebar",   "Sidebar",       show=False),
        Binding("escape",     "cancel_stream",    "Cancel",        show=False),
        Binding("ctrl+enter", "send_message",     "Send",          show=False),
    ]

    DEFAULT_CSS = """
    ChatScreen {
        background: #0d0d0d;
        layout: vertical;
    }

    /* ── custom header ───────────────────────────────────────────── */
    #chat-header {
        height: 3;
        background: #141414;
        border-bottom: tall #ff8c00;
        layout: horizontal;
        align: left middle;
        padding: 0 2;
    }

    #header-logo {
        color: #ff8c00;
        text-style: bold;
        width: auto;
        margin-right: 2;
    }

    #header-sep {
        color: #2a2a2a;
        width: auto;
        margin-right: 2;
    }

    #header-model {
        color: #ffb347;
        width: auto;
        margin-right: 2;
    }

    #header-status {
        color: #39d353;
        text-style: bold;
        width: 1fr;
    }

    #header-time {
        color: #3a3a3a;
        width: auto;
    }

    /* ── body (sidebar + chat log) ───────────────────────────────── */
    #body {
        layout: horizontal;
        height: 1fr;
    }

    /* ── chat log ────────────────────────────────────────────────── */
    #chat-log-container {
        width: 1fr;
        height: 100%;
        background: #0d0d0d;
        padding: 0;
    }

    #chat-log {
        width: 100%;
        height: 100%;
        background: #0d0d0d;
        scrollbar-color: #2a2a2a;
        scrollbar-color-hover: #ff8c00;
        padding: 1 2;
    }

    /* ── thinking indicator ──────────────────────────────────────── */
    #thinking-bar {
        height: 1;
        background: #141414;
        color: #ff8c00;
        text-style: bold italic;
        padding: 0 2;
        display: none;
    }

    #thinking-bar.visible {
        display: block;
    }

    /* ── footer ──────────────────────────────────────────────────── */
    #chat-footer {
        height: 1;
        background: #141414;
        border-top: tall #2a2a2a;
        color: #3a3a3a;
        text-align: center;
        padding: 0 1;
    }
    """

    _streaming: reactive[bool] = reactive(False)
    _sidebar_visible: reactive[bool] = reactive(True)
    _history: list[ChatMessage] = []
    _agent = None
    _stream_worker: Worker | None = None

    # ── compose ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        # Header
        with Horizontal(id="chat-header"):
            yield Static("🐦‍🔥  ASHBORN", id="header-logo")
            yield Static("│", id="header-sep")
            yield Static("Loading...", id="header-model")
            yield Static("│", id="header-sep")
            yield Static("● Initializing", id="header-status")
            yield Static("", id="header-time")

        # Body
        with Horizontal(id="body"):
            yield SidebarWidget(id="sidebar")
            with Container(id="chat-log-container"):
                yield RichLog(
                    id="chat-log",
                    highlight=True,
                    markup=True,
                    wrap=True,
                    auto_scroll=True,
                )

        # Thinking bar
        yield Static("", id="thinking-bar")

        # Input
        yield ChatInputBar(id="input-bar")

        # Footer
        yield Static(
            " Enter: New-line  │  Ctrl+Enter: Send  │  Ctrl+L: Clear  │  Ctrl+K: Config  │  Ctrl+B: Sidebar  │  Ctrl+Q: Quit",
            id="chat-footer",
        )

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._print_welcome()
        self._load_model_info()
        self.query_one("#input-bar", ChatInputBar).focus_input()
        self.set_interval(1.0, self._tick_time)
        # Start loading agent in background
        self._init_agent_worker()

    def _tick_time(self) -> None:
        try:
            t = datetime.now().strftime("%H:%M:%S")
            self.query_one("#header-time", Static).update(f"[#3a3a3a]{t}[/]")
        except Exception:
            pass

    def _load_model_info(self) -> None:
        load_dotenv(override=True)
        model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o")
        self.query_one("#header-model", Static).update(f"[#ffb347]{model}[/]")
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.model_name = model

    # ── welcome banner ────────────────────────────────────────────────────────

    def _print_welcome(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(Text.from_markup(
            "[bold #ff8c00]╔══════════════════════════════════════════════════════╗[/]"
        ))
        log.write(Text.from_markup(
            "[bold #ff8c00]║[/]  [bold white]🐦‍🔥  ASHBORN AGENT[/]  [dim]— Powered by Phoenix AI[/]     [bold #ff8c00]║[/]"
        ))
        log.write(Text.from_markup(
            "[bold #ff8c00]║[/]  [dim]Type your message and press [bold #00d4ff]Ctrl+Enter[/] to send.[/]   [bold #ff8c00]║[/]"
        ))
        log.write(Text.from_markup(
            "[bold #ff8c00]║[/]  [dim]Press [bold #00d4ff]Ctrl+K[/] to reconfigure API settings.[/]       [bold #ff8c00]║[/]"
        ))
        log.write(Text.from_markup(
            "[bold #ff8c00]╚══════════════════════════════════════════════════════╝[/]"
        ))
        log.write("")

    # ── agent initialization ──────────────────────────────────────────────────

    @work(exclusive=True, thread=True, name="init-agent")
    def _init_agent_worker(self) -> None:
        """Load the agent in a background thread so UI stays responsive."""
        import asyncio as _asyncio
        loop = _asyncio.new_event_loop()
        try:
            agent = loop.run_until_complete(self._load_agent())
            self._agent = agent
            self.call_from_thread(self._on_agent_ready)
        except Exception as e:
            self.call_from_thread(self._on_agent_error, str(e))
        finally:
            loop.close()

    async def _load_agent(self):
        from agent import get_ashborn_agent
        load_dotenv(override=True)
        return await get_ashborn_agent()

    def _on_agent_ready(self) -> None:
        self._set_status("● Ready", "#39d353")
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.status = "● Ready"

    def _on_agent_error(self, err: str) -> None:
        self._set_status("● Error", "#ff4444")
        log = self.query_one("#chat-log", RichLog)
        log.write(Text.from_markup(
            f"[bold #ff4444]⚠  Agent initialization failed:[/] [#e0e0e0]{err}[/]\n"
            f"[dim]Press [bold #00d4ff]Ctrl+K[/] to check your configuration.[/]\n"
        ))

    # ── key handlers ─────────────────────────────────────────────────────────

    def on_key(self, event) -> None:
        """Intercept Ctrl+Enter to send."""
        if event.key == "ctrl+enter":
            event.prevent_default()
            self.action_send_message()

    # ── actions ───────────────────────────────────────────────────────────────

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_clear_chat(self) -> None:
        self._history.clear()
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        self._print_welcome()
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.message_count = 0

    def action_open_config(self) -> None:
        from cli.setup_wizard import SetupWizard
        self.app.push_screen(SetupWizard(), callback=self._on_config_closed)

    def _on_config_closed(self, _result=None) -> None:
        # Reload model info after config changes
        self._load_model_info()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", SidebarWidget)
        self._sidebar_visible = not self._sidebar_visible
        if self._sidebar_visible:
            sidebar.remove_class("hidden")
        else:
            sidebar.add_class("hidden")

    def action_cancel_stream(self) -> None:
        if self._stream_worker and self._stream_worker.is_running:
            self._stream_worker.cancel()
            self._streaming = False
            self._set_thinking(False)
            self._set_status("● Ready", "#39d353")

    def action_send_message(self) -> None:
        input_bar = self.query_one("#input-bar", ChatInputBar)
        text = input_bar.get_text().strip()
        if not text:
            return
        if self._streaming:
            self.notify("⚡ Already processing — press Esc to cancel.", severity="warning")
            return
        if not self._agent:
            self.notify("⏳ Agent still loading, please wait...", severity="warning")
            return

        input_bar.clear()
        input_bar.focus_input()
        self._render_user_message(text)
        self._start_stream(text)

    # ── message rendering ─────────────────────────────────────────────────────

    def _render_user_message(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        ts = datetime.now().strftime("%H:%M")
        log.write(Text.from_markup(
            f"[bold #00d4ff]┌─ You[/] [dim]({ts})[/]"
        ))
        # Wrap long lines
        for line in text.splitlines():
            log.write(Text.from_markup(f"[bold #00d4ff]│[/] [#e0e0e0]{line}[/]"))
        log.write(Text.from_markup("[bold #00d4ff]└" + "─" * 54 + "[/]"))
        log.write("")
        msg = ChatMessage("user", text)
        self._history.append(msg)
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.message_count = len(self._history)

    def _render_assistant_message(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        ts = datetime.now().strftime("%H:%M")
        log.write(Text.from_markup(
            f"[bold #ff8c00]┌─ 🐦‍🔥 Ashborn[/] [dim]({ts})[/]"
        ))
        log.write(Text.from_markup("[bold #ff8c00]│[/]"))
        # Render markdown inside the panel
        log.write(Markdown(text))
        log.write(Text.from_markup("[bold #ff8c00]└" + "─" * 54 + "[/]"))
        log.write("")
        msg = ChatMessage("assistant", text)
        self._history.append(msg)
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.message_count = len(self._history)

    # ── streaming ─────────────────────────────────────────────────────────────

    def _start_stream(self, user_text: str) -> None:
        self._streaming = True
        self._set_status("⠋ Thinking...", "#ffb347")
        self._set_thinking(True, "🐦‍🔥  Ashborn is focusing...")
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.status = "⠋ Thinking..."
        self._stream_worker = self.run_stream_worker(user_text)

    @work(exclusive=True, thread=True, name="stream-response")
    def run_stream_worker(self, user_text: str) -> None:
        """Run the agent stream in a background thread."""
        import asyncio as _asyncio
        loop = _asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._stream_response(user_text))
        except Exception as e:
            self.call_from_thread(self._on_stream_error, str(e))
        finally:
            loop.close()
            self.call_from_thread(self._on_stream_done)

    async def _stream_response(self, user_text: str) -> None:
        full_response = ""
        phase = "status"  # "status" -> "streaming"

        gen = self._agent.run_stream(user_text, mode="auto")

        async for event in gen:
            if event["type"] == "status":
                self.call_from_thread(
                    self._set_thinking, True, f"🐦‍🔥  {event['content']}"
                )
            elif event["type"] == "chunk":
                if phase == "status":
                    # First content chunk — switch to streaming display
                    phase = "streaming"
                    self.call_from_thread(self._set_thinking, False)
                    self.call_from_thread(self._set_status, "⠿ Streaming...", "#ffb347")
                full_response += event["content"]
                # Update the log incrementally
                self.call_from_thread(self._update_stream_display, full_response)

        # Final commit
        if full_response:
            self.call_from_thread(self._commit_response, full_response)

    def _update_stream_display(self, text: str) -> None:
        """Show a live streaming indicator in the thinking bar."""
        # Keep thinking bar updated with token count during stream
        preview = text.split("\n")[0][:60]
        self._set_thinking(True, f"⠿  [dim]{preview}…[/]", markup=True)

    def _commit_response(self, text: str) -> None:
        """Called once after streaming finishes — renders the full response."""
        self._set_thinking(False)
        self._render_assistant_message(text)

    def _on_stream_done(self) -> None:
        self._streaming = False
        self._set_status("● Ready", "#39d353")
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.status = "● Ready"

    def _on_stream_error(self, err: str) -> None:
        self._set_thinking(False)
        log = self.query_one("#chat-log", RichLog)
        log.write(Text.from_markup(f"[bold #ff4444]⚠  Error:[/] [#e0e0e0]{err}[/]\n"))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = "#39d353") -> None:
        try:
            self.query_one("#header-status", Static).update(
                f"[bold {color}]{text}[/]"
            )
        except Exception:
            pass

    def _set_thinking(self, visible: bool, msg: str = "", markup: bool = False) -> None:
        bar = self.query_one("#thinking-bar", Static)
        if visible:
            bar.add_class("visible")
            if markup:
                bar.update(Text.from_markup(f"  {msg}"))
            else:
                bar.update(f"  {msg}")
        else:
            bar.remove_class("visible")
            bar.update("")
