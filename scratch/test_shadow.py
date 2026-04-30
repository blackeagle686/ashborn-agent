from textual.app import App, ComposeResult
from textual.widgets import Static

class TestApp(App):
    CSS = """
    Static {
        outline: solid #FFD700;
    }
    """
    def compose(self) -> ComposeResult:
        yield Static("Test")

if __name__ == "__main__":
    app = TestApp()
    try:
        app.run()
    except Exception as e:
        print(e)
