import re

with open('ashborn/cli/setup_wizard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
content = content.replace(
    'from textual.containers import Container, Vertical, Horizontal',
    'from textual.containers import Container, Vertical, Horizontal, VerticalScroll'
)

# 2. CSS updates
css_old = """    #wizard-card {
        width: 70;
        height: auto;
        background: #15173D;"""
css_new = """    #wizard-card {
        width: 70;
        height: auto;
        max-height: 90vh;
        background: #15173D;
        
    }
    VerticalScroll {
        height: 1fr;
        padding-right: 1;
        scrollbar-color: #982598;
        scrollbar-color-hover: #FF6B00;"""
content = content.replace(css_old, css_new)

# 3. Form fields
form_old = """            with Vertical():
                yield Label("API Key", classes="field-label")
                yield Label("Your OpenAI-compatible API key", classes="field-hint")
                yield Input(
                    placeholder="sk-... or ak_...",
                    password=True,
                    id="inp-api-key",
                )

                yield Label("Model Name", classes="field-label")
                yield Label("The model identifier to use", classes="field-hint")
                yield Input(
                    placeholder="gpt-4o / LongCat-Flash-Lite / ...",
                    id="inp-model",
                )

                yield Label("API Base URL", classes="field-label")
                yield Label("Leave default for OpenAI, or set a custom endpoint", classes="field-hint")
                yield Input(
                    placeholder="https://api.openai.com/v1",
                    id="inp-base-url",
                )"""

form_new = """            with VerticalScroll():
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
                yield Input(placeholder="all-MiniLM-L6-v2", id="inp-embedding")"""
content = content.replace(form_old, form_new)

# 4. on_mount
on_mount_old = """    def on_mount(self) -> None:
        \"\"\"Pre-fill saved values from .env if they exist.\"\"\"
        existing = _read_env()
        if existing.get("OPENAI_API_KEY"):
            self.query_one("#inp-api-key", Input).value = existing["OPENAI_API_KEY"]
        if existing.get("OPENAI_LLM_MODEL"):
            self.query_one("#inp-model", Input).value = existing["OPENAI_LLM_MODEL"]
        if existing.get("OPENAI_BASE_URL"):
            self.query_one("#inp-base-url", Input).value = existing["OPENAI_BASE_URL"]
        # Focus first empty field
        for field_id in ("#inp-api-key", "#inp-model", "#inp-base-url"):
            inp = self.query_one(field_id, Input)
            if not inp.value:
                inp.focus()
                return
        self.query_one("#inp-api-key", Input).focus()"""

on_mount_new = """    def on_mount(self) -> None:
        \"\"\"Pre-fill saved values from .env if they exist.\"\"\"
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
        self.query_one("#inp-api-key", Input).focus()"""
content = content.replace(on_mount_old, on_mount_new)

# 5. handle_input_submitted
sub_old = """    def handle_input_submitted(self, event: Input.Submitted) -> None:
        \"\"\"Tab through fields on Enter, save on last field.\"\"\"
        order = ["#inp-api-key", "#inp-model", "#inp-base-url"]"""
sub_new = """    def handle_input_submitted(self, event: Input.Submitted) -> None:
        \"\"\"Tab through fields on Enter, save on last field.\"\"\"
        order = ["#inp-api-key", "#inp-model", "#inp-base-url", "#inp-log-level", "#inp-redis-url", "#inp-vector-db", "#inp-chroma-dir", "#inp-embedding"]"""
content = content.replace(sub_old, sub_new)

# 6. _do_save
save_old = """    def _do_save(self) -> None:
        api_key  = self.query_one("#inp-api-key",  Input).value.strip()
        model    = self.query_one("#inp-model",    Input).value.strip()
        base_url = self.query_one("#inp-base-url", Input).value.strip()

        # Validation
        errors = []
        if not api_key:
            errors.append("#inp-api-key")
        if not model:
            errors.append("#inp-model")

        # Clear previous error state
        for field_id in ("#inp-api-key", "#inp-model", "#inp-base-url"):
            self.query_one(field_id, Input).remove_class("error")

        if errors:
            for field_id in errors:
                self.query_one(field_id, Input).add_class("error")
            self._set_status("⚠  API Key and Model Name are required.", "error")
            return

        # Set defaults
        if not base_url:
            base_url = "https://api.openai.com/v1"

        # Write to .env
        _write_env({
            "OPENAI_API_KEY":   api_key,
            "OPENAI_LLM_MODEL": model,
            "OPENAI_BASE_URL":  base_url,
        })"""

save_new = """    def _do_save(self) -> None:
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
        _write_env(updates)"""
content = content.replace(save_old, save_new)

with open('ashborn/cli/setup_wizard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Wizard updated successfully.")
