"""GoNoGo TUI — Visual score bar (0-100)."""

from textual.widgets import Static
from textual.reactive import reactive


class ScoreBar(Static):
    """Displays a 0-100 score as a colored progress bar with label."""

    score: reactive[int] = reactive(0)
    label: reactive[str] = reactive("Overall Score")
    bar_width: int = 40

    DEFAULT_CSS = """
    ScoreBar {
        height: 1;
        padding: 0 1;
    }
    """

    def watch_score(self) -> None:
        self._render_bar()

    def watch_label(self) -> None:
        self._render_bar()

    def _render_bar(self) -> None:
        score = max(0, min(100, self.score))
        filled = round(self.bar_width * score / 100)
        empty = self.bar_width - filled

        if score >= 80:
            color = "green"
        elif score >= 60:
            color = "yellow"
        elif score >= 40:
            color = "dark_orange"
        else:
            color = "red"

        bar = f"[{color}]{'█' * filled}[/][#555555]{'░' * empty}[/]"
        self.update(f"{self.label}: {bar} {score}/100")
