"""GoNoGo TUI — Colored verdict badge widget."""

from textual.widgets import Static
from textual.reactive import reactive


class VerdictBadge(Static):
    """Displays GO / NO-GO / GO WITH CONDITIONS as a colored badge."""

    verdict: reactive[str] = reactive("")

    DEFAULT_CSS = """
    VerdictBadge {
        width: auto;
        min-width: 20;
        height: 3;
        text-align: center;
        text-style: bold;
        padding: 1 3;
        margin: 1 0;
    }
    VerdictBadge.go {
        background: #16a34a;
        color: #ffffff;
    }
    VerdictBadge.nogo {
        background: #dc2626;
        color: #ffffff;
    }
    VerdictBadge.conditional {
        background: #d97706;
        color: #ffffff;
    }
    VerdictBadge.unknown {
        background: $surface;
        color: $text-muted;
    }
    """

    def watch_verdict(self, value: str) -> None:
        self.remove_class("go", "nogo", "conditional", "unknown")

        if value == "GO":
            self.add_class("go")
            self.update("GO")
        elif value == "NO-GO":
            self.add_class("nogo")
            self.update("NO-GO")
        elif value == "GO_WITH_CONDITIONS":
            self.add_class("conditional")
            self.update("GO WITH CONDITIONS")
        else:
            self.add_class("unknown")
            self.update(value or "---")
