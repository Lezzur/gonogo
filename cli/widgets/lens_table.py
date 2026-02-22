"""GoNoGo TUI — 7-lens score breakdown table widget."""

from textual.widgets import Static
from textual.reactive import reactive


LENS_DISPLAY_NAMES = {
    "functionality": "Functionality",
    "design": "Design",
    "ux": "UX",
    "performance": "Performance",
    "accessibility": "Accessibility",
    "code_content": "Code/Content",
    "security": "Security",
}

LENS_ORDER = [
    "functionality",
    "design",
    "ux",
    "performance",
    "accessibility",
    "code_content",
    "security",
]


def _grade_color(grade: str) -> str:
    colors = {
        "A": "green",
        "B": "#22c55e",
        "C": "yellow",
        "D": "dark_orange",
        "F": "red",
    }
    return colors.get(grade, "white")


class LensTable(Static):
    """Renders a formatted table of the 7 lens scores."""

    lens_scores: reactive[dict] = reactive({}, always_update=True)

    DEFAULT_CSS = """
    LensTable {
        padding: 1 2;
    }
    """

    def watch_lens_scores(self) -> None:
        self._render_table()

    def _render_table(self) -> None:
        if not self.lens_scores:
            self.update("[dim]No lens data available[/]")
            return

        lines = []
        header = f"{'Lens':<16} {'Score':>5}  {'Grade':>5}  Summary"
        lines.append(f"[bold]{header}[/bold]")
        lines.append("─" * 70)

        for key in LENS_ORDER:
            data = self.lens_scores.get(key, {})
            if not data:
                continue

            name = LENS_DISPLAY_NAMES.get(key, key)
            score = data.get("score", 0)
            grade = data.get("grade", "?")
            summary = data.get("summary", "")

            color = _grade_color(grade)
            # Truncate summary to fit
            max_summary = 40
            if len(summary) > max_summary:
                summary = summary[: max_summary - 1] + "…"

            lines.append(
                f"{name:<16} [{color}]{score:>5}[/]  [{color}]{grade:>5}[/]  {summary}"
            )

        self.update("\n".join(lines))
