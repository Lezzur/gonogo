"""GoNoGo TUI — Home screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical
from textual.widgets import Button, Static


class HomeScreen(Screen):
    """Main menu: New Scan, History, Settings, Quit."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        with Container(id="home-container"):
            yield Static(
                r"""
   ____       _   _        ____
  / ___| ___ | \ | | ___  / ___| ___
 | |  _ / _ \|  \| |/ _ \| |  _ / _ \
 | |_| | (_) | |\  | (_) | |_| | (_) |
  \____|\___/|_| \_|\___/ \____|\___/
""",
                id="home-title",
            )
            yield Static(
                "Ship-readiness scanner — Evaluate any web app across 7 quality lenses",
                id="home-subtitle",
            )
            with Vertical(id="home-menu"):
                yield Button("[n] New Scan", id="btn-new-scan", variant="primary")
                yield Button("[t] Scan History", id="btn-history", variant="default")
                yield Button("[s] Settings", id="btn-settings", variant="default")
                yield Button("[q] Quit", id="btn-quit", variant="error")
            yield Static("v2.0.0-tui", id="home-version")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-new-scan":
            self.app.action_new_scan()
        elif button_id == "btn-history":
            self.app.action_history()
        elif button_id == "btn-settings":
            self.app.action_settings()
        elif button_id == "btn-quit":
            self.app.exit()
