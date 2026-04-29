"""
Ashborn Agent — Main Full-Screen Chat UI.

Layout:
  ┌─ Header ─────────────────────────────────────────────────────┐
  │ 🐦‍🔥 ASHBORN  │  model name  │  status badge                  │
  ├─ Body ──────────────────────────────────────────────────────┤
  │ Sidebar (collapsible) │  Chat window (scrollable messages)  │
  │                       │  [ThinkingSpinner — animated]       │
  ├─ Input bar ──────────────────────────────────────────────────┤
  │ > prompt here...                              [nn chars]     │
  ├─ Footer ─────────────────────────────────────────────────────┤
  │  Ctrl+Enter: Send  Ctrl+L: Clear  Ctrl+K: Config  Ctrl+Q: Quit │
  └──────────────────────────────────────────────────────────────┘
"""

import asyncio
from datetime import datetime
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, TextArea, RichLog, Label
from textual.containers import Container, Vertical, Horizontal
from textual.binding import Binding
from textual.reactive import reactive
from textual import on, work
from textual.worker import Worker
from textual.message import Message
from rich.text import Text
from rich.markdown import Markdown

import os
from dotenv import load_dotenv


# ── Message data class ────────────────────────────────────────────────────────

class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
        self.timestamp = datetime.now().strftime("%H:%M")


# ── Animated thinking spinner ─────────────────────────────────────────────────

class ThinkingSpinner(Static):
    """Braille-frame animated spinner — shown inside chat area while agent thinks."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    DEFAULT_CSS = """
    ThinkingSpinner {
        height: 0;
        background: #1a1a1a;
        border-top: tall #ff8c00 20%;
        border-bottom: tall #ff8c00 20%;
        color: #ff8c00;
        text-style: bold;
        padding: 0 2;
        margin: 1 2;
    }
    ThinkingSpinner.visible {
        height: 3;
    }
    """

    _frame_idx: int = 0
    _label: str = "Ashborn is thinking"

    def on_mount(self) -> None:
        self.set_interval(0.09, self._tick)

    def _tick(self) -> None:
        if "visible" not in self.classes:
            return
        self._frame_idx = (self._frame_idx + 1) % len(self.FRAMES)
        frame = self.FRAMES[self._frame_idx]
        dots = "." * ((self._frame_idx % 3) + 1)
        self.update(
            Text.from_markup(
                f"  [bold #ff8c00]{frame}[/]  [#ffb347]{self._label}[/][dim #666666]{dots}[/]"
            )
        )

    def show(self, label: str = "Ashborn is thinking") -> None:
        self._label = label
        self.add_class("visible")

    def hide(self) -> None:
        self.remove_class("visible")
        self.update("")


# ── Custom TextArea — fires SendMessage on Ctrl+Enter ─────────────────────────

class ChatTextArea(TextArea):
    """TextArea that fires a SendMessage event on Ctrl+Enter."""

    class SendMessage(Message):
        """Posted when user presses Ctrl+Enter."""
        bubble = True

    def _on_key(self, event) -> None:
        if event.key in ("ctrl+enter", "ctrl+j"):
            event.prevent_default()
            event.stop()
            self.post_message(self.SendMessage())
            self.app.notify("Sending...", timeout=1)
        else:
            super()._on_key(event)


# ── Sidebar ───────────────────────────────────────────────────────────────────

class SidebarWidget(Vertical):
    """Collapsible left sidebar — session stats & keyboard shortcuts."""

    DEFAULT_CSS = """
    SidebarWidget {
        width: 26;
        min-width: 26;
        background: #141414;
        border-right: tall #2a2a2a;
        padding: 1 1;
        display: none; /* Hidden by default for 'Simple' look */
    }
    SidebarWidget.visible { display: block; }

    .sb-title {
        color: #ff8c00;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }
    .sb-div {
        color: #2a2a2a;
        width: 100%;
        margin-bottom: 1;
    }
    .sb-label {
        color: #666666;
        width: 100%;
        margin-bottom: 0;
    }
    .sb-val {
        color: #e0e0e0;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }
    .sc-row {
        color: #666666;
        width: 100%;
    }
    """

    message_count: reactive[int] = reactive(0)
    status: reactive[str]        = reactive("● Initializing")
    model_name: reactive[str]    = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("🐦‍🔥  ASHBORN", classes="sb-title")
        yield Static("─" * 22, classes="sb-div")

        yield Static("Model", classes="sb-label")
        yield Static("—", id="sb-model", classes="sb-val")

        yield Static("Status", classes="sb-label")
        yield Static("● Initializing", id="sb-status", classes="sb-val")

        yield Static("Messages", classes="sb-label")
        yield Static("0", id="sb-msgs", classes="sb-val")

        yield Static("─" * 22, classes="sb-div")
        yield Static("Shortcuts", classes="sb-title")
        yield Static("─" * 22, classes="sb-div")

        shortcuts = [
            ("Ctrl+Enter", "Send"),
            ("Enter",      "New line"),
            ("Ctrl+L",     "Clear chat"),
            ("Ctrl+K",     "Config"),
            ("Ctrl+B",     "Sidebar"),
            ("Ctrl+Q",     "Quit"),
            ("Esc",        "Cancel"),
        ]
        for key, desc in shortcuts:
            yield Static(
                f"[bold #00d4ff]{key:<12}[/] [#666666]{desc}[/]",
                classes="sc-row",
                markup=True,
            )

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


# ── Input bar ─────────────────────────────────────────────────────────────────

class ChatInputBar(Horizontal):
    """Bottom input bar — prefix + textarea + char counter."""

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
    ChatTextArea {
        background: #1a1a1a;
        border: tall #2a2a2a;
        color: #e0e0e0;
        width: 1fr;
        height: 3;
    }
    ChatTextArea:focus {
        border: tall #ff8c00;
        background: #1f1f1f;
    }
    #char-counter {
        color: #3a3a3a;
        width: auto;
        padding: 0 1;
        margin-top: 1;
    }
    #char-counter.warn   { color: #ffd700; }
    #char-counter.danger { color: #ff4444; }
    """

    MAX_CHARS = 4096

    def compose(self) -> ComposeResult:
        yield Static("❯", id="input-prefix")
        yield ChatTextArea(id="chat-input", language=None)
        yield Static("0", id="char-counter")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        count = len(event.text_area.text)
        counter = self.query_one("#char-counter", Static)
        counter.update(str(count))
        counter.remove_class("warn", "danger")
        if count > self.MAX_CHARS * 0.9:
            counter.add_class("danger")
        elif count > self.MAX_CHARS * 0.7:
            counter.add_class("warn")

    def get_text(self) -> str:
        return self.query_one("#chat-input", ChatTextArea).text

    def clear(self) -> None:
        ta = self.query_one("#chat-input", ChatTextArea)
        ta.load_text("")
        self.query_one("#char-counter", Static).update("0")

    def focus_input(self) -> None:
        self.query_one("#chat-input", ChatTextArea).focus()


# ── Main Chat Screen ──────────────────────────────────────────────────────────

class ChatScreen(Screen):
    """Full-screen interactive chat interface."""

    BINDINGS = [
        Binding("ctrl+q", "quit_app",       "Quit",    show=False),
        Binding("ctrl+l", "clear_chat",     "Clear",   show=False),
        Binding("ctrl+k", "open_config",    "Config",  show=False),
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=False),
        Binding("escape", "cancel_stream",  "Cancel",  show=False),
    ]

    DEFAULT_CSS = """
    ChatScreen {
        background: #0d0d0d;
        layout: vertical;
    }

    /* ── Header ── */
    #chat-header {
        height: 3;
        background: #0d0d0d;
        border-bottom: tall #ff8c00 10%;
        layout: horizontal;
        align: left middle;
        padding: 0 2;
    }
    #header-logo {
        color: #ff8c00;
        text-style: bold;
        width: auto;
    }
    #header-status {
        color: #39d353;
        text-style: italic;
        width: 1fr;
        text-align: right;
    }

    /* ── Body ── */
    #body {
        layout: horizontal;
        height: 1fr;
    }
    #chat-log-container {
        width: 1fr;
        height: 100%;
        background: #0d0d0d;
        layout: vertical;
    }
    #chat-log {
        width: 100%;
        height: 1fr;
        background: #0d0d0d;
        scrollbar-color: #2a2a2a;
        scrollbar-color-hover: #ff8c00;
        padding: 1 2;
    }

    /* ── Footer ── */
    #chat-footer {
        height: 1;
        background: #141414;
        border-top: tall #2a2a2a;
        color: #3a3a3a;
        text-align: center;
        padding: 0 1;
    }
    """

    _streaming: reactive[bool]       = reactive(False)
    _sidebar_visible: reactive[bool] = reactive(False)
    _history: list[ChatMessage]      = []
    _agent                           = None
    _stream_worker: Worker | None    = None

    # ── compose ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        # Header
        with Horizontal(id="chat-header"):
            yield Static("🐦‍🔥  ASHBORN", id="header-logo")
            yield Static("● Initializing", id="header-status")

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
                # Animated spinner lives BELOW the log, inside the same column
                yield ThinkingSpinner(id="thinking-spinner")

        # Input + Footer
        yield ChatInputBar(id="input-bar")
        yield Static(
            " Ctrl+Enter: Send  │  Enter: New-line  │  Ctrl+L: Clear  │  Ctrl+K: Config  │  Ctrl+B: Sidebar  │  Ctrl+Q: Quit",
            id="chat-footer",
        )

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._print_welcome()
        self._load_model_info()
        self.query_one("#input-bar", ChatInputBar).focus_input()
        self._init_agent_worker()

    def _load_model_info(self) -> None:
        load_dotenv(override=True)
        model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o")
        self.query_one("#sidebar", SidebarWidget).model_name = model

    # ── welcome banner ────────────────────────────────────────────────────────

    def _print_welcome(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write("")
        log.write(Text.from_markup("[bold #ff8c00]🐦‍🔥  How can I help you today?[/]"))
        log.write(Text.from_markup("[dim]Type your request below and press [bold #00d4ff]Ctrl+Enter[/] to send.[/]"))
        log.write("")

    # ── agent init ────────────────────────────────────────────────────────────

    @work(exclusive=True, name="init-agent")
    async def _init_agent_worker(self) -> None:
        try:
            from agent import get_ashborn_agent
            load_dotenv(override=True)
            self._agent = await get_ashborn_agent()
            self._on_agent_ready()
        except Exception as e:
            self._on_agent_error(str(e))

    def _on_agent_ready(self) -> None:
        self._set_status("● Ready", "#39d353")
        self.query_one("#sidebar", SidebarWidget).status = "● Ready"

    def _on_agent_error(self, err: str) -> None:
        self._set_status("● Error", "#ff4444")
        log = self.query_one("#chat-log", RichLog)
        log.write(Text.from_markup(
            f"[bold #ff4444]⚠  Agent init failed:[/] [#e0e0e0]{err}[/]\n"
            f"[dim]Press [bold #00d4ff]Ctrl+K[/] to check your configuration.[/]\n"
        ))

    # ── SendMessage from ChatTextArea ─────────────────────────────────────────

    @on(ChatTextArea.SendMessage)
    def handle_send_message(self, _event: ChatTextArea.SendMessage) -> None:
        self._do_send()

    # ── actions ───────────────────────────────────────────────────────────────

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_clear_chat(self) -> None:
        self._history.clear()
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        self._print_welcome()
        self.query_one("#sidebar", SidebarWidget).message_count = 0

    def action_open_config(self) -> None:
        from cli.setup_wizard import SetupWizard
        self.app.push_screen(SetupWizard(), callback=self._on_config_closed)

    def _on_config_closed(self, _result=None) -> None:
        self._load_model_info()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", SidebarWidget)
        self._sidebar_visible = not self._sidebar_visible
        if self._sidebar_visible:
            sidebar.add_class("visible")
        else:
            sidebar.remove_class("visible")

    def action_cancel_stream(self) -> None:
        if self._stream_worker and self._stream_worker.is_running:
            self._stream_worker.cancel()
        self._streaming = False
        self.query_one("#thinking-spinner", ThinkingSpinner).hide()
        self._set_status("● Ready", "#39d353")
        self.query_one("#sidebar", SidebarWidget).status = "● Ready"

    # ── core send ─────────────────────────────────────────────────────────────

    def _do_send(self) -> None:
        input_bar = self.query_one("#input-bar", ChatInputBar)
        text = input_bar.get_text().strip()
        if not text:
            return
        if self._streaming:
            self.notify("⚡ Already processing — press Esc to cancel.", severity="warning")
            return

        # ✅ Clear the screen for a fresh focus on this turn
        log = self.query_one("#chat-log", RichLog)
        log.clear()

        # Clear input and render user bubble at the top
        input_bar.clear()
        input_bar.focus_input()
        self._render_user_message(text)

        if not self._agent:
            self.notify("⏳ Agent still loading, please wait...", severity="warning")
            return

        self._start_stream(text)

    # ── rendering ─────────────────────────────────────────────────────────────

    def _render_user_message(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        ts = datetime.now().strftime("%H:%M")
        log.write(Text.from_markup(f"[bold #00d4ff]┌─ You[/] [dim]({ts})[/]"))
        for line in text.splitlines():
            # In Rich markup, '[' is escaped by doubling it to '[['
            safe = line.replace("[", "[[")
            log.write(Text.from_markup(f"[bold #00d4ff]│[/] [#e0e0e0]{safe}[/]"))
        log.write(Text.from_markup("[bold #00d4ff]└" + "─" * 54 + "[/]"))
        log.write("") # RichLog handles newlines better this way
        self._history.append(ChatMessage("user", text))
        self.query_one("#sidebar", SidebarWidget).message_count = len(self._history)

    def _render_assistant_message(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        ts = datetime.now().strftime("%H:%M")
        log.write(Text.from_markup(f"[bold #ff8c00]┌─ 🐦‍🔥 Ashborn[/] [dim]({ts})[/]"))
        log.write(Text.from_markup("[bold #ff8c00]│[/]"))
        log.write(Markdown(text))
        log.write(Text.from_markup("[bold #ff8c00]└" + "─" * 54 + "[/]"))
        log.write("")
        log.scroll_end(animate=False)
        self._history.append(ChatMessage("assistant", text))
        self.query_one("#sidebar", SidebarWidget).message_count = len(self._history)

    # ── streaming ─────────────────────────────────────────────────────────────

    def _start_stream(self, user_text: str) -> None:
        self._streaming = True
        self.query_one("#sidebar", SidebarWidget).status = "⠋ Thinking..."
        self._set_status("⠋ Thinking...", "#ffb347")
        self.query_one("#thinking-spinner", ThinkingSpinner).show("Ashborn is thinking")
        self._stream_worker = self.run_stream_worker(user_text)

    @work(exclusive=True, name="stream-response")
    async def run_stream_worker(self, user_text: str) -> None:
        try:
            await self._stream_response(user_text)
        except Exception as e:
            self._on_stream_error(str(e))
        finally:
            self._on_stream_done()

    async def _stream_response(self, user_text: str) -> None:
        full_response = ""
        phase = "status"
        spinner = self.query_one("#thinking-spinner", ThinkingSpinner)

        gen = self._agent.run_stream(user_text, mode="auto")

        async for event in gen:
            if event["type"] == "status":
                # Update spinner label with agent status messages
                spinner.show(event["content"][:55])
            elif event["type"] == "chunk":
                if phase == "status":
                    phase = "streaming"
                    self._set_status("⠿ Streaming...", "#ffb347")
                full_response += event["content"]
                preview = full_response.split("\n")[0][:50]
                spinner.show(f"Writing: {preview}…")

        if full_response:
            self._commit_response(full_response)

    def _commit_response(self, text: str) -> None:
        self.query_one("#thinking-spinner", ThinkingSpinner).hide()
        self._render_assistant_message(text)

    def _on_stream_done(self) -> None:
        self._streaming = False
        self._set_status("● Ready", "#39d353")
        self.query_one("#sidebar", SidebarWidget).status = "● Ready"

    def _on_stream_error(self, err: str) -> None:
        self.query_one("#thinking-spinner", ThinkingSpinner).hide()
        log = self.query_one("#chat-log", RichLog)
        log.write(Text.from_markup(f"[bold #ff4444]⚠  Error:[/] [#e0e0e0]{err}[/]\n"))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = "#39d353") -> None:
        try:
            self.query_one("#header-status", Static).update(f"[bold {color}]{text}[/]")
        except Exception:
            pass
