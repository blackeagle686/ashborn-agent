from textual.app import App, ComposeResult
from textual.widgets import TextArea

class TestApp(App):
    def compose(self) -> ComposeResult:
        yield TextArea("Hello world", read_only=True, id="text")

if __name__ == "__main__":
    app = TestApp()
    try:
        app.run()
    except Exception as e:
        print(e)
