"""
Ashborn Agent — First-run Setup Wizard Screen.
Collects API Key, Model Name, and Base URL, then writes them to .env.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Static, Input, Button, Label
)
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.binding import Binding
from textual import on
from textual.reactive import reactive

from pathlib import Path
import re


# ── Configuration Path ────────────────────────────────────────────────────────
# Use local .env if it exists, otherwise use the global home directory one
LOCAL_ENV = Path(".env")
GLOBAL_CONFIG_DIR = Path.home() / ".ashborn"
GLOBAL_ENV = GLOBAL_CONFIG_DIR / ".env"

def _get_env_path() -> Path:
    if LOCAL_ENV.exists():
        return LOCAL_ENV
    if not GLOBAL_CONFIG_DIR.exists():
        GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return GLOBAL_ENV

LOGO_ART = """\
  ╔═╗ ╔═╗╦ ╦╔╗ ╔═╗╦═╗╔╗╔
  ╠═╣ ╚═╗╠═╣╠╩╗║ ║╠╦╝║║║
  ╩ ╩o╚═╝╩ ╩╚═╝╚═╝╩╚═╝╚╝\
"""


class SetupWizard(Screen):
    """Full-screen first-run configuration wizard."""

    BINDINGS = [
        Binding("ctrl+q", "quit_app", "Quit", show=True),
        Binding("escape",  "quit_app", "Quit", show=False),
        Binding("enter",   "save",     "Save & Start", show=False),
        Binding("tab",     "focus_next", "Next Field", show=False),
    ]

    DEFAULT_CSS = """
    SetupWizard {
        background: #1B1F24;
        align: center middle;
    }

    /* ── outer glow card ─────────────────────────────────────────── */
    #wizard-card {
        width: 70;
        height: auto;
        max-height: 90vh;
        background: #1B1F24;
        
    }
    VerticalScroll {
        height: 1fr;
        padding-right: 1;
        scrollbar-color: #2E333A;
        scrollbar-color-hover: #A89F91;
        border: round #2E333A;
        padding: 2 4;
        align: center middle;
    }

    /* ── logo ────────────────────────────────────────────────────── */
    #logo {
        text-align: center;
        color: #FF6B00;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }

    #logo-sub {
        text-align: center;
        color: #A89F91;
        width: 100%;
        margin-bottom: 2;
    }

    /* ── section label ───────────────────────────────────────────── */
    .field-label {
        color: #A89F91;
        text-style: bold;
        margin-bottom: 0;
        padding-left: 1;
    }

    .field-hint {
        color: #A89F91;
        opacity: 0.7;
        margin-bottom: 1;
        padding-left: 1;
    }

    /* ── inputs ──────────────────────────────────────────────────── */
    Input {
        background: #1B1F24;
        border: round #2E333A;
        color: #F1E9DD;
        margin-bottom: 1;
        width: 100%;
    }

    Input:focus {
        border: round #A89F91;
        background: #1B1F24;
    }

    Input.error {
        border: round #ff4444;
    }

    /* ── divider ─────────────────────────────────────────────────── */
    #divider {
        height: 1;
        color: #2E333A;
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }

    /* ── button row ──────────────────────────────────────────────── */
    #btn-row {
        align: center middle;
        width: 100%;
        margin-top: 1;
        height: auto;
    }

    #btn-save {
        background: #A89F91;
        color: #1B1F24;
        text-style: bold;
        border: none;
        padding: 0 6;
        min-width: 22;
    }

    #btn-save:hover {
        background: #F1E9DD;
    }

    #btn-skip {
        background: #1B1F24;
        color: #A89F91;
        border: round #2E333A;
        padding: 0 4;
        margin-left: 2;
    }

    #btn-skip:hover {
        color: #F1E9DD;
        border: round #A89F91;
    }

    /* ── status message ──────────────────────────────────────────── */
    #status-msg {
        text-align: center;
        width: 100%;
        height: 1;
        margin-top: 1;
        color: transparent;
    }

    #status-msg.success {
        color: #39d353;
        text-style: bold;
    }

    #status-msg.error {
        color: #ff4444;
        text-style: bold;
    }

    /* ── footer hint ─────────────────────────────────────────────── */
    #wizard-footer {
        text-align: center;
        color: #A89F91;
        width: 100%;
        margin-top: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="wizard-card"):
            yield Static(LOGO_ART, id="logo")
            yield Static("🐦‍🔥  Powered by Phoenix AI Framework", id="logo-sub")
            yield Static("─" * 58, id="divider")

            with VerticalScroll():
                yield Label("API Key", classes="field-label")
                yield Label("Your OpenAI-compatible API key", classes="field-hint")
                yield Input(placeholder="sk-... or ak_...", password=True, id="inp-api-key")

                yield Label("Model Name", classes="field-label")
                yield Label("The model identifier to use", classes="field-hint")
                yield Input(placeholder="gpt-4o / LongCat-Flash-Lite / ...", id="inp-model")

                yield Label("API Base URL", classes="field-label")
                yield Label("Leave default for OpenAI, or set a custom endpoint", classes="field-hint")
                yield Input(placeholder="https://api.openai.com/v1", id="inp-base-url")

                yield Label("Log Level", classes="field-label")
                yield Label("DEBUG, INFO, WARNING, ERROR", classes="field-hint")
                yield Input(placeholder="INFO", id="inp-log-level")

                yield Label("Redis URL", classes="field-label")
                yield Label("URL for Redis cache (e.g. redis://localhost:6379)", classes="field-hint")
                yield Input(placeholder="redis://localhost:6379", id="inp-redis-url")

                yield Label("Vector DB Type", classes="field-label")
                yield Label("Type of vector DB (e.g. chroma)", classes="field-hint")
                yield Input(placeholder="chroma", id="inp-vector-db")

                yield Label("Chroma Persist Dir", classes="field-label")
                yield Label("Path to save vector embeddings", classes="field-hint")
                yield Input(placeholder="./chroma_db", id="inp-chroma-dir")

                yield Label("Embedding Model", classes="field-label")
                yield Label("HuggingFace model name for embeddings", classes="field-hint")
                yield Input(placeholder="all-MiniLM-L6-v2", id="inp-embedding")

            yield Static("", id="status-msg")

            with Horizontal(id="btn-row"):
                yield Button("  Save & Start  🚀", id="btn-save", variant="primary")
                yield Button("Skip →", id="btn-skip", variant="default")

            yield Static(
                "Tab: next field  │  Enter: save  │  Ctrl+Q: quit",
                id="wizard-footer",
            )

    def on_mount(self) -> None:
        """Pre-fill saved values from .env if they exist."""
        existing = _read_env()
        mappings = {
            "OPENAI_API_KEY": "#inp-api-key",
            "OPENAI_LLM_MODEL": "#inp-model",
            "OPENAI_BASE_URL": "#inp-base-url",
            "LOG_LEVEL": "#inp-log-level",
            "REDIS_URL": "#inp-redis-url",
            "VECTOR_DB_TYPE": "#inp-vector-db",
            "CHROMA_PERSIST_DIR": "#inp-chroma-dir",
            "EMBEDDING_MODEL": "#inp-embedding"
        }
        for env_key, widget_id in mappings.items():
            if existing.get(env_key):
                try:
                    self.query_one(widget_id, Input).value = existing[env_key]
                except Exception:
                    pass

        # Focus first empty field
        all_fields = list(mappings.values())
        for field_id in all_fields:
            try:
                inp = self.query_one(field_id, Input)
                if not inp.value:
                    inp.focus()
                    return
            except Exception:
                pass
        self.query_one("#inp-api-key", Input).focus()

    # ── actions ───────────────────────────────────────────────────────────────

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_save(self) -> None:
        self._do_save()

    @on(Button.Pressed, "#btn-save")
    def handle_save(self) -> None:
        self._do_save()

    @on(Button.Pressed, "#btn-skip")
    def handle_skip(self) -> None:
        """Skip wizard and go straight to chat (using whatever .env has)."""
        from .chat_screen import ChatScreen
        self.app.switch_screen(ChatScreen())

    @on(Input.Submitted)
    def handle_input_submitted(self, event: Input.Submitted) -> None:
        """Tab through fields on Enter, save on last field."""
        order = ["#inp-api-key", "#inp-model", "#inp-base-url", "#inp-log-level", "#inp-redis-url", "#inp-vector-db", "#inp-chroma-dir", "#inp-embedding"]
        current_id = f"#{event.input.id}"
        idx = order.index(current_id) if current_id in order else -1
        if idx < len(order) - 1:
            self.query_one(order[idx + 1], Input).focus()
        else:
            self._do_save()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _do_save(self) -> None:
        api_key  = self.query_one("#inp-api-key",  Input).value.strip()
        model    = self.query_one("#inp-model",    Input).value.strip()
        base_url = self.query_one("#inp-base-url", Input).value.strip()
        
        log_lvl  = self.query_one("#inp-log-level", Input).value.strip()
        redis    = self.query_one("#inp-redis-url", Input).value.strip()
        vdb      = self.query_one("#inp-vector-db", Input).value.strip()
        cdir     = self.query_one("#inp-chroma-dir", Input).value.strip()
        embed    = self.query_one("#inp-embedding", Input).value.strip()

        # Validation
        errors = []
        if not api_key:
            errors.append("#inp-api-key")
        if not model:
            errors.append("#inp-model")

        # Clear previous error state
        all_fields = ["#inp-api-key", "#inp-model", "#inp-base-url", "#inp-log-level", "#inp-redis-url", "#inp-vector-db", "#inp-chroma-dir", "#inp-embedding"]
        for field_id in all_fields:
            self.query_one(field_id, Input).remove_class("error")

        if errors:
            for field_id in errors:
                self.query_one(field_id, Input).add_class("error")
            self._set_status("⚠  API Key and Model Name are required.", "error")
            return

        # Set defaults
        if not base_url:
            base_url = "https://api.openai.com/v1"

        updates = {
            "OPENAI_API_KEY":   api_key,
            "OPENAI_LLM_MODEL": model,
            "OPENAI_BASE_URL":  base_url,
        }
        if log_lvl: updates["LOG_LEVEL"] = log_lvl
        if redis: updates["REDIS_URL"] = redis
        if vdb: updates["VECTOR_DB_TYPE"] = vdb
        if cdir: updates["CHROMA_PERSIST_DIR"] = cdir
        if embed: updates["EMBEDDING_MODEL"] = embed

        # Write to .env
        _write_env(updates)

        self._set_status("✓  Configuration saved successfully!", "success")

        # Brief pause then switch to chat
        self.set_timer(0.8, self._launch_chat)

    def _launch_chat(self) -> None:
        # If we were pushed (as a settings screen), just dismiss
        if len(self.app.screen_stack) > 1:
            self.dismiss(True)
        else:
            # First run: switch to chat
            from .chat_screen import ChatScreen
            self.app.switch_screen(ChatScreen())

    def _set_status(self, msg: str, kind: str) -> None:
        widget = self.query_one("#status-msg", Static)
        widget.update(msg)
        widget.remove_class("success", "error")
        widget.add_class(kind)


# ── .env helpers ──────────────────────────────────────────────────────────────

def _read_env() -> dict:
    """Parse .env into a dict (simple key=value, ignoring comments)."""
    env_path = _get_env_path()
    result = {}
    if not env_path.exists():
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^([A-Z0-9_]+)\s*=\s*"?(.*?)"?\s*$', line)
        if m:
            result[m.group(1)] = m.group(2)
    return result


def _write_env(updates: dict) -> None:
    """Upsert keys into .env, preserving all other lines and comments."""
    env_path = _get_env_path()
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    written_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            m = re.match(r'^([A-Z0-9_]+)\s*=', stripped)
            if m and m.group(1) in updates:
                key = m.group(1)
                new_lines.append(f'{key}="{updates[key]}"')
                written_keys.add(key)
                continue
        new_lines.append(line)

    # Append any keys not already in the file
    for key, val in updates.items():
        if key not in written_keys:
            new_lines.append(f'{key}="{val}"')

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
