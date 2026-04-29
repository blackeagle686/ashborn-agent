import os

with open('ashborn/cli/chat_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
content = content.replace(
    'from textual.widgets import Static, TextArea, RichLog, Label',
    'from textual.widgets import Static, TextArea, RichLog, Label, Select'
)

# 2. ChatInputBar CSS
css_old = """    #char-counter {
        color: #982598;
        width: auto;
        padding: 0 1;
        margin-top: 1;
    }"""
css_new = """    Select {
        width: 14;
        height: 3;
        margin-top: 1;
        margin-left: 1;
        background: #15173D;
        border: round #982598;
        color: #F1E9E9;
    }
    Select:focus {
        border: round #E491C9;
    }
    #char-counter {
        color: #982598;
        width: auto;
        padding: 0 1;
        margin-top: 1;
    }"""
content = content.replace(css_old, css_new)

# 3. ChatInputBar Compose
comp_old = """    def compose(self) -> ComposeResult:
        yield Static("❯", id="input-prefix")
        yield ChatTextArea(id="chat-input", language=None)
        yield Static("0", id="char-counter")"""
comp_new = """    def compose(self) -> ComposeResult:
        yield Static("❯", id="input-prefix")
        yield ChatTextArea(id="chat-input", language=None)
        yield Select([("Auto", "auto"), ("Plan", "plan"), ("Fast", "fast_ans")], value="auto", id="mode-select")
        yield Static("0", id="char-counter")"""
content = content.replace(comp_old, comp_new)

# 4. _do_send
send_old = """    def _do_send(self) -> None:
        input_bar = self.query_one("#input-bar", ChatInputBar)
        text = input_bar.get_text().strip()"""
send_new = """    def _do_send(self) -> None:
        input_bar = self.query_one("#input-bar", ChatInputBar)
        text = input_bar.get_text().strip()
        mode = input_bar.query_one("#mode-select", Select).value"""
content = content.replace(send_old, send_new)

call_old = """        self._start_stream(text)"""
call_new = """        self._start_stream(text, mode)"""
content = content.replace(call_old, call_new)

# 5. _start_stream
stream_old = """    def _start_stream(self, user_text: str) -> None:
        self._streaming = True
        self.query_one("#sidebar", SidebarWidget).status = "⠋ Thinking..."
        self._set_status("⠋ Thinking...", "#E491C9")
        self.query_one("#thinking-spinner", ThinkingSpinner).show("Ashborn is thinking")
        self._stream_worker = self.run_stream_worker(user_text)

    @work(exclusive=True, name="stream-response")
    async def run_stream_worker(self, user_text: str) -> None:
        try:
            await self._stream_response(user_text)"""

stream_new = """    def _start_stream(self, user_text: str, mode: str) -> None:
        self._streaming = True
        self.query_one("#sidebar", SidebarWidget).status = "⠋ Thinking..."
        self._set_status("⠋ Thinking...", "#E491C9")
        self.query_one("#thinking-spinner", ThinkingSpinner).show("Ashborn is thinking")
        self._stream_worker = self.run_stream_worker(user_text, mode)

    @work(exclusive=True, name="stream-response")
    async def run_stream_worker(self, user_text: str, mode: str) -> None:
        try:
            await self._stream_response(user_text, mode)"""
content = content.replace(stream_old, stream_new)

# 6. _stream_response
resp_old = """    async def _stream_response(self, user_text: str) -> None:
        full_response = ""
        phase = "status"
        spinner = self.query_one("#thinking-spinner", ThinkingSpinner)

        gen = self._agent.run_stream(user_text, mode="auto")"""
resp_new = """    async def _stream_response(self, user_text: str, mode: str) -> None:
        full_response = ""
        phase = "status"
        spinner = self.query_one("#thinking-spinner", ThinkingSpinner)

        gen = self._agent.run_stream(user_text, mode=mode)"""
content = content.replace(resp_old, resp_new)

with open('ashborn/cli/chat_screen.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated Select successfully")
