"""GoNoGo TUI — Rotating tip bar footer widget."""

from textual.widgets import Static
from textual.reactive import reactive
from cli.tips import TIPS


class TipBar(Static):
    """Footer widget that cycles through tips every 12 seconds."""

    tip_index: reactive[int] = reactive(0)

    DEFAULT_CSS = """
    TipBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        text-align: center;
        padding: 0 1;
    }
    """

    def on_mount(self) -> None:
        self._update_tip()
        self.set_interval(12.0, self._advance_tip)

    def _advance_tip(self) -> None:
        self.tip_index = (self.tip_index + 1) % len(TIPS)

    def watch_tip_index(self) -> None:
        self._update_tip()

    def _update_tip(self) -> None:
        if TIPS:
            self.update(f" TIP: {TIPS[self.tip_index]}")
