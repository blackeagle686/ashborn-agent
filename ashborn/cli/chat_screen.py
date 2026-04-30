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
from textual.widgets import Static, TextArea, RichLog, Label, Select, Button
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
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
        background: #12161D;
        border-top: round #FF7B00 20%;
        border-bottom: round #FF7B00 20%;
        color: #E6EDF3;
        text-style: bold;
        padding: 0 2;
        margin: 1 4;
        outline: solid #FFD70022;
        opacity: 0;
        transition: height 300ms, opacity 300ms;
    }
    ThinkingSpinner.visible {
        height: 3;
        opacity: 1;
        min-height: 3;
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
                f"  [bold #FF7B00]{frame}[/]  [#8B949E]{self._label}[/][dim #D4AF37]{dots}[/]"
            )
        )

    def show(self, label: str = "Ashborn is thinking") -> None:
        self._label = label
        self.add_class("visible")

    def hide(self) -> None:
        self.remove_class("visible")
        self.update("")


# ── Message Display Widget with Copy Button ───────────────────────────────────

class MessageDisplay(Horizontal):
    """A widget to display a single message with a copy button."""
    
    DEFAULT_CSS = """
    MessageDisplay {
        height: auto;
        margin-bottom: 1;
        padding: 0 2;
        opacity: 0;
    }
    MessageDisplay.mounted {
        opacity: 1;
        transition: opacity 500ms;
    }
    .msg-content-container {
        width: 1fr;
        height: auto;
        background: #1C2128;
        border: round #30363D;
        padding: 0 1;
    }
    .msg-content-container.user {
        background: #12161D;
        border: round #FF7B00;
        margin-left: 10;
    }
    .msg-content-container.assistant {
        background: #1C2128;
        border: round #D4AF37;
        margin-right: 10;
        outline: solid #FFD70011;
    }
    .msg-header {
        height: 1;
        margin: 0 1;
        color: #8B949E;
        text-style: bold;
    }
    .msg-body {
        height: auto;
        padding: 0 1;
        color: #E6EDF3;
    }
    .msg-btn {
        width: 8;
        min-width: 8;
        height: 3;
        margin-left: 1;
        background: #1C2128;
        border: round #D4AF37;
        color: #E6EDF3;
        text-style: bold;
        padding: 0;
    }
    .msg-btn:hover {
        background: #D4AF37;
        color: #0A0C10;
        border: round #FFD700;
    }
    .msg-action-column {
        width: 9;
        height: auto;
        align: center top;
    }
    """

    def __init__(self, message: ChatMessage, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def on_mount(self) -> None:
        self.add_class("mounted")

    def compose(self) -> ComposeResult:
        role_class = self.message.role
        with Vertical(classes=f"msg-content-container {role_class}"):
            # Header with role and timestamp
            if self.message.role == "user":
                yield Label(f"YOU  •  {self.message.timestamp}", classes="msg-header")
            else:
                yield Label(f"ASHBORN  •  {self.message.timestamp}", classes="msg-header")
            
            # Content
            content = self.message.content
            if self.message.role == "user":
                safe_content = content.replace("[", "[[")
                yield Static(safe_content, classes="msg-body")
            else:
                yield Static(Markdown(content), classes="msg-body")

        if self.message.role == "assistant":
            with Vertical(classes="msg-action-column"):
                yield Button("Copy", classes="msg-btn", id="copy-btn")
                yield Button("Reply", classes="msg-btn", id="reply-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-btn":
            self.app.copy_to_clipboard(self.message.content)
            self.notify("✓ Copied to clipboard", severity="information")
        elif event.button.id == "reply-btn":
            # Quote the message in the input area
            chat_screen = self.app.query_one(ChatScreen)
            input_bar = chat_screen.query_one("#chat-input", ChatTextArea)
            quote = f"> {self.message.content.splitlines()[0]}...\n"
            input_bar.load_text(quote)
            input_bar.focus()
            self.notify("↩ Quoted response", severity="information")


# ── Custom TextArea — fires SendMessage on Ctrl+Enter ─────────────────────────

class ChatTextArea(TextArea):
    """TextArea that fires a SendMessage event on Ctrl+Enter."""

    class SendMessage(Message):
        """Posted when user presses Ctrl+Enter."""
        bubble = True

    def on_key(self, event) -> None:
        # Plain Enter or Ctrl+J (fallback) sends the message
        if event.key in ("enter", "ctrl+j"):
            event.prevent_default()
            event.stop()
            self.post_message(self.SendMessage())
        # Ctrl+Enter or Shift+Enter inserts a newline
        elif event.key in ("ctrl+enter", "shift+enter"):
            # Manually insert a newline since we stopped the default
            self.insert("\n")
            event.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────

class SidebarWidget(Vertical):
    """Collapsible left sidebar — session stats & keyboard shortcuts."""

    DEFAULT_CSS = """
    SidebarWidget {
        width: 28;
        background: #12161D;
        border-right: thick #30363D;
        padding: 1 2;
        margin: 1 0 1 1;
        outline: solid #FFD70011;
        display: none;
    }
    SidebarWidget.visible { display: block; }

    .sb-title {
        color: #D4AF37;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }
    .sb-div {
        color: #30363D;
        width: 100%;
        margin-bottom: 1;
    }
    .sb-label {
        color: #8B949E;
        width: 100%;
    }
    .sb-val {
        color: #E6EDF3;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }
    .sc-row {
        color: #8B949E;
        width: 100%;
        padding: 0 1;
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
            ("Enter",       "Send"),
            ("Shift+Enter", "New line"),
            ("Ctrl+L",      "Clear chat"),
            ("Ctrl+K",      "Config"),
            ("Ctrl+B",      "Sidebar"),
            ("Ctrl+Y",      "Copy Last"),
            ("Ctrl+Q",      "Quit"),
            ("Esc",        "Cancel"),
        ]
        for key, desc in shortcuts:
            yield Static(
                f"[bold #A89F91]{key:<12}[/] [#A89F91]{desc}[/]",
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
        background: #12161D;
        border-top: thick #30363D;
        padding: 0 2;
        align: left middle;
        margin: 0 1 1 1;
        outline: solid #FFD70011;
    }
    #input-prefix {
        color: #FF7B00;
        text-style: bold;
        width: auto;
        padding: 0 1;
    }
    ChatTextArea {
        background: #0A0C10;
        border: round #30363D;
        color: #E6EDF3;
        width: 1fr;
        height: 3;
    }
    ChatTextArea:focus {
        border: round #FF7B00;
    }
    Select {
        width: 16;
        height: 1;
        margin-left: 1;
        background: #0A0C10;
        border: round #30363D;
        color: #E6EDF3;
    }
    Select:focus {
        border: round #D4AF37;
    }
    #char-counter {
        color: #8B949E;
        width: auto;
        padding: 0 1;
    }
    #char-counter.warn   { color: #D4AF37; }
    #char-counter.danger { color: #DA3633; }
    """

    MAX_CHARS = 4096

    def compose(self) -> ComposeResult:
        yield Static("❯", id="input-prefix")
        yield ChatTextArea(id="chat-input", language=None)
        yield Select([("Auto", "auto"), ("Plan", "plan"), ("Fast", "fast_ans")], value="auto", id="mode-select")
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
        Binding("ctrl+l", "clear_chat",     "Clear",   show=False),
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=False),
        Binding("ctrl+y", "copy_last",      "Copy Last", show=False),
        Binding("escape", "cancel_stream",  "Cancel",  show=False),
    ]

    DEFAULT_CSS = """
    ChatScreen {
        background: #0A0C10;
        layout: vertical;
    }

    /* ── Header ── */
    #chat-header {
        height: 3;
        background: #12161D;
        border-bottom: thick #30363D;
        layout: horizontal;
        align: left middle;
        padding: 0 4;
        margin: 1 1 0 1;
        outline: solid #FFD70011;
    }
    #header-logo {
        color: #FF7B00;
        text-style: bold;
        width: auto;
    }
    #header-status {
        color: #238636;
        text-style: bold italic;
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
        background: #0A0C10;
        layout: vertical;
    }
    #chat-log {
        width: 100%;
        height: 1fr;
        background: #0A0C10;
        scrollbar-color: #30363D;
        scrollbar-color-hover: #D4AF37;
        scrollbar-gutter: stable;
        padding: 1 2;
        overflow-y: scroll;
    }

    /* ── Footer ── */
    #chat-footer {
        height: 1;
        background: #12161D;
        color: #8B949E;
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
                with VerticalScroll(id="chat-log"):
                    # Welcome messages will be mounted here
                    pass
                # Animated spinner lives BELOW the log, inside the same column
                yield ThinkingSpinner(id="thinking-spinner")

        # Input + Footer
        yield ChatInputBar(id="input-bar")
        yield Static(
            " Enter: Send  │  Ctrl+Y: Copy Last  │  Ctrl+L: Clear  │  Ctrl+K: Config  │  Ctrl+B: Sidebar  │  Ctrl+Q: Quit",
            id="chat-footer",
        )

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        # We don't need to set can_focus on VerticalScroll as it handles children
        
        self._print_welcome()
        self._load_model_info()
        self.query_one("#input-bar", ChatInputBar).focus_input()
        self._init_agent_worker()

    def _load_model_info(self) -> None:
        from pathlib import Path
        local_env = Path(".env")
        global_env = Path.home() / ".ashborn" / ".env"
        
        if local_env.exists():
            load_dotenv(local_env, override=True)
        elif global_env.exists():
            load_dotenv(global_env, override=True)
        else:
            load_dotenv(override=True) # Fallback to default behavior

        model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o")
        self.query_one("#sidebar", SidebarWidget).model_name = model

    # ── welcome banner ────────────────────────────────────────────────────────

    def _print_welcome(self) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        log.mount(Static(""))
        log.mount(Static("[bold #FF7B00]🐦‍🔥  Greetings. I am Ashborn.[/]", markup=True))
        log.mount(Static("[dim #8B949E]The Ultimate Autonomous Architect is ready to manifest your vision.[/]", markup=True))
        log.mount(Static(""))

    # ── agent init ────────────────────────────────────────────────────────────

    @work(exclusive=True, name="init-agent")
    async def _init_agent_worker(self) -> None:
        try:
            from ..agent import get_ashborn_agent
            from pathlib import Path
            local_env = Path(".env")
            global_env = Path.home() / ".ashborn" / ".env"
            
            if local_env.exists():
                load_dotenv(local_env, override=True)
            elif global_env.exists():
                load_dotenv(global_env, override=True)

            self._agent = await get_ashborn_agent()
            self._on_agent_ready()
        except Exception as e:
            self._on_agent_error(str(e))

    def _on_agent_ready(self) -> None:
        self._set_status("● Ready", "#39d353")
        self.query_one("#sidebar", SidebarWidget).status = "● Ready"

    def _on_agent_error(self, err: str) -> None:
        self._set_status("● Error", "#ff4444")
        log = self.query_one("#chat-log", VerticalScroll)
        log.mount(Static(
            f"[bold #ff4444]⚠  Agent init failed:[/] [#F1E9DD]{err}[/]\n"
            f"[dim]Press [bold #A89F91]Ctrl+K[/] to check your configuration.[/]\n",
            markup=True
        ))

    # ── SendMessage from ChatTextArea ─────────────────────────────────────────

    @on(ChatTextArea.SendMessage)
    def handle_send_message(self, _event: ChatTextArea.SendMessage) -> None:
        self._do_send()

    # ── actions ───────────────────────────────────────────────────────────────


    def action_clear_chat(self) -> None:
        self._history.clear()
        log = self.query_one("#chat-log", VerticalScroll)
        # Remove all MessageDisplay widgets
        for child in log.children[:]:
            child.remove()
        self._print_welcome()
        self.query_one("#sidebar", SidebarWidget).message_count = 0


    def _on_config_closed(self, result=None) -> None:
        if result:
            from phoenix.core.config import config
            config.reload()
            
            self._load_model_info()
            # Re-initialize the agent with new configuration
            self._init_agent_worker()
            self.notify("✓ Configuration updated. Agent re-initialized.", severity="information")

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

    def action_copy_last(self) -> None:
        """Copies the last assistant response to the clipboard."""
        # Find the last assistant message in history
        assistant_msgs = [m for m in self._history if m.role == "assistant"]
        if assistant_msgs:
            last_msg = assistant_msgs[-1].content
            try:
                self.app.copy_to_clipboard(last_msg)
                self.notify("✓ Last response copied to clipboard", severity="information")
            except Exception:
                self.notify("⚠ Clipboard copy failed (OSC 52 not supported?)", severity="error")
        else:
            self.notify("No response to copy", severity="warning")

    # ── core send ─────────────────────────────────────────────────────────────

    def _do_send(self) -> None:
        input_bar = self.query_one("#input-bar", ChatInputBar)
        text = input_bar.get_text().strip()
        mode = input_bar.query_one("#mode-select", Select).value
        if not text:
            return
        if self._streaming:
            self.notify("⚡ Already processing — press Esc to cancel.", severity="warning")
            return

        # ✅ Clear the screen for a fresh focus on this turn
        log = self.query_one("#chat-log", VerticalScroll)
        for child in log.children[:]:
            child.remove()

        # Clear input and render user bubble at the top
        input_bar.clear()
        input_bar.focus_input()
        self._render_user_message(text)

        if not self._agent:
            self.notify("⏳ Agent still loading, please wait...", severity="warning")
            return

        self._start_stream(text, mode)

    # ── rendering ─────────────────────────────────────────────────────────────

    def _render_user_message(self, text: str) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        msg = ChatMessage("user", text)
        log.mount(MessageDisplay(msg))
        log.scroll_end(animate=False)
        self._history.append(msg)
        self.query_one("#sidebar", SidebarWidget).message_count = len(self._history)

    def _render_assistant_message(self, text: str) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        msg = ChatMessage("assistant", text)
        log.mount(MessageDisplay(msg))
        log.scroll_end(animate=False)
        self._history.append(msg)
        self.query_one("#sidebar", SidebarWidget).message_count = len(self._history)

    # ── streaming ─────────────────────────────────────────────────────────────

    def _start_stream(self, user_text: str, mode: str) -> None:
        self._streaming = True
        self.query_one("#sidebar", SidebarWidget).status = "⠋ Thinking..."
        self._set_status("⠋ Thinking...", "#A89F91")
        self.query_one("#thinking-spinner", ThinkingSpinner).show("Ashborn is thinking")
        self._stream_worker = self.run_stream_worker(user_text, mode)

    @work(exclusive=True, name="stream-response")
    async def run_stream_worker(self, user_text: str, mode: str) -> None:
        try:
            await self._stream_response(user_text, mode)
        except Exception as e:
            self._on_stream_error(str(e))
        finally:
            self._on_stream_done()

    async def _stream_response(self, user_text: str, mode: str) -> None:
        full_response = ""
        phase = "status"
        spinner = self.query_one("#thinking-spinner", ThinkingSpinner)

        gen = self._agent.run_stream(user_text, mode=mode)

        async for event in gen:
            if event["type"] == "status":
                # Update spinner label with agent status messages
                spinner.show(event["content"][:55])
            elif event["type"] == "thought":
                # NEW: Capture planner reasoning text and show in UI
                reasoning = event["content"]
                # Show a scrolling preview of the thinking process
                spinner.show(f"Thinking: {reasoning[-60:]}")
            elif event["type"] == "chunk":
                if phase == "status":
                    phase = "streaming"
                    self._set_status("⠿ Streaming...", "#A89F91")
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
        log = self.query_one("#chat-log", VerticalScroll)
        log.mount(Static(f"[bold #ff4444]⚠  Error:[/] [#F1E9DD]{err}[/]\n", markup=True))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = "#39d353") -> None:
        try:
            self.query_one("#header-status", Static).update(f"[bold {color}]{text}[/]")
        except Exception:
            pass
