"""GoNoGo TUI — Results screen showing verdict, scores, findings, and top actions."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static
from textual.binding import Binding

from cli.backend_bridge import get_scan
from cli.widgets.verdict_badge import VerdictBadge
from cli.widgets.score_bar import ScoreBar
from cli.widgets.lens_table import LensTable


class ResultsScreen(Screen):
    """Displays scan results: verdict, score, lens breakdown, top actions."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("f", "fix_loop", "Fix Loop"),
    ]

    def __init__(self, scan_id: str) -> None:
        super().__init__()
        self.scan_id = scan_id
        self._scan_data: dict = {}

    def on_mount(self) -> None:
        self._scan_data = get_scan(self.scan_id) or {}
        self._populate()

    def compose(self) -> ComposeResult:
        with Container(id="results-container"):
            yield Static("[bold]Scan Results[/bold]")
            yield Static("", id="results-url")

            # Warnings (if any)
            yield Static("", id="results-warnings")

            with Horizontal(id="results-header"):
                with Vertical(id="results-verdict-area"):
                    yield VerdictBadge(id="verdict-badge")
                with Vertical(id="results-score-area"):
                    yield ScoreBar(id="score-bar")
                    yield Static("", id="results-grade")
                    yield Static("", id="results-duration")

            # Top 3 actions
            with Vertical(id="results-actions"):
                yield Static("[bold]Top 3 Actions[/bold]", id="results-actions-title")
                yield Static("", id="results-actions-list")

            # Findings summary
            yield Static("", id="results-findings-summary")

            # Lens breakdown
            yield LensTable(id="lens-table")

            yield Static(
                "\n[dim]Press [bold][f][/bold] to start fix loop "
                "| [bold][escape][/bold] to go back[/]",
            )

    def _populate(self) -> None:
        data = self._scan_data
        if not data:
            self.query_one("#results-url", Static).update("[red]Scan not found.[/]")
            return

        # URL
        self.query_one("#results-url", Static).update(
            f"URL: [bold]{data.get('url', 'N/A')}[/]"
        )

        # Warnings
        warnings = data.get("warnings", [])
        if warnings:
            warning_text = "\n".join(f"  ! {w}" for w in warnings)
            self.query_one("#results-warnings", Static).update(
                f"[bold]Warnings:[/bold]\n{warning_text}"
            )

        # Verdict
        verdict = data.get("verdict", "")
        self.query_one("#verdict-badge", VerdictBadge).verdict = verdict

        # Score
        score = data.get("overall_score", 0) or 0
        self.query_one("#score-bar", ScoreBar).score = score

        # Grade
        grade = data.get("overall_grade", "?")
        self.query_one("#results-grade", Static).update(f"Grade: [bold]{grade}[/]")

        # Duration
        duration = data.get("duration_seconds")
        if duration:
            self.query_one("#results-duration", Static).update(
                f"Duration: {duration:.1f}s"
            )

        # Top 3 actions
        actions = data.get("top_3_actions", [])
        if actions:
            actions_text = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(actions))
            self.query_one("#results-actions-list", Static).update(actions_text)
        else:
            self.query_one("#results-actions-list", Static).update(
                "[dim]No actions available.[/]"
            )

        # Findings summary
        findings = data.get("findings_count", {})
        if findings:
            parts = []
            for severity in ["critical", "high", "medium", "low"]:
                count = findings.get(severity, 0)
                if count:
                    color = {
                        "critical": "red",
                        "high": "dark_orange",
                        "medium": "yellow",
                        "low": "dim",
                    }.get(severity, "white")
                    parts.append(f"[{color}]{severity}: {count}[/]")
            if parts:
                self.query_one("#results-findings-summary", Static).update(
                    "[bold]Findings:[/bold]  " + "  |  ".join(parts)
                )

        # Lens scores
        lens_scores = data.get("lens_scores", {})
        self.query_one("#lens-table", LensTable).lens_scores = lens_scores

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_fix_loop(self) -> None:
        from cli.screens.fix_loop import FixLoopScreen
        self.app.push_screen(FixLoopScreen(self.scan_id))
