"""GoNoGo TUI — Main application."""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.binding import Binding

from cli.widgets.tip_bar import TipBar
from cli.backend_bridge import is_backend_available, initialize_database


class GoNoGoApp(App):
    """GoNoGo Terminal UI."""

    TITLE = "GoNoGo"
    SUB_TITLE = "Ship-readiness scanner"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("h", "go_home", "Home", show=True),
        Binding("n", "new_scan", "New Scan", show=True),
        Binding("t", "history", "History", show=True),
        Binding("s", "settings", "Settings", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def on_mount(self) -> None:
        # Initialize DB on startup
        if is_backend_available():
            try:
                initialize_database()
            except Exception:
                pass  # Will show error when user tries to scan

        # Push home screen
        from cli.screens.home import HomeScreen
        self.push_screen(HomeScreen())

    def compose(self) -> ComposeResult:
        yield TipBar()

    def action_go_home(self) -> None:
        from cli.screens.home import HomeScreen
        self._switch_screen(HomeScreen)

    def action_new_scan(self) -> None:
        from cli.screens.scan import ScanScreen
        self._switch_screen(ScanScreen)

    def action_history(self) -> None:
        from cli.screens.history import HistoryScreen
        self._switch_screen(HistoryScreen)

    def action_settings(self) -> None:
        from cli.screens.settings import SettingsScreen
        self._switch_screen(SettingsScreen)

    def _switch_screen(self, screen_cls: type) -> None:
        """Pop all screens down to base, then push the target screen."""
        # Pop back to the base (keep only the default screen)
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(screen_cls())
