from textual.app import App, ComposeResult
from textual.widgets import RichLog

class TestApp(App):
    CSS = """
    RichLog {
        user-select: text;
    }
    """
    def compose(self) -> ComposeResult:
        yield RichLog(id="log", selectable=True)

    def on_mount(self) -> None:
        self.query_one("#log").write("Hello world")

if __name__ == "__main__":
    app = TestApp()
    try:
        app.run()
    except Exception as e:
        print(e)
