"""GoNoGo TUI — History screen with DataTable of past scans."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import DataTable, Static

from cli.backend_bridge import is_backend_available, list_scans


class HistoryScreen(Screen):
    """Displays a table of past scans. Select a row to view results."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._scans: list[dict] = []

    def compose(self) -> ComposeResult:
        with Container(id="history-container"):
            yield Static("[bold]Scan History[/bold]", id="history-title")
            yield DataTable(id="history-table")
            yield Static(
                "[dim]Select a row to view results | [bold][escape][/bold] to go back[/]"
            )

    def on_mount(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Date", "URL", "Status", "Verdict", "Score", "Grade")

        if not is_backend_available():
            table.add_row("--", "Backend not available", "--", "--", "--", "--")
            return

        self._scans = list_scans(limit=50)
        if not self._scans:
            table.add_row("--", "No scans yet. Press [n] to start one.", "--", "--", "--", "--")
            return

        for scan in self._scans:
            date = (scan.get("created_at") or "")[:19]
            url = scan.get("url", "")
            # Truncate long URLs
            if len(url) > 40:
                url = url[:37] + "..."
            status = scan.get("status", "")
            verdict = scan.get("verdict") or "--"
            score = str(scan.get("overall_score") or "--")
            grade = scan.get("overall_grade") or "--"

            table.add_row(date, url, status, verdict, score, grade)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_index = event.cursor_row
        if 0 <= row_index < len(self._scans):
            scan = self._scans[row_index]
            scan_id = scan.get("id")
            if scan_id and scan.get("status") == "completed":
                from cli.screens.results import ResultsScreen
                self.app.push_screen(ResultsScreen(scan_id))

    def action_go_back(self) -> None:
        self.app.pop_screen()
