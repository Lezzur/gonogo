"""GoNoGo TUI — Scan screen with URL input and live progress."""

import asyncio
import json

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical
from textual.widgets import Button, Input, Label, ProgressBar, Static
from textual import work

from cli.config import load_config
from cli.backend_bridge import (
    is_backend_available,
    create_scan_record,
    launch_scan,
    subscribe_progress,
)


class ScanScreen(Screen):
    """URL input + live progress bar."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._scan_id: str | None = None
        self._scanning = False

    def compose(self) -> ComposeResult:
        cfg = load_config()
        with Container(id="scan-container"):
            yield Static("[bold]New Scan[/bold]", id="scan-title")

            with Vertical(id="scan-form"):
                yield Label("Target URL:")
                yield Input(
                    placeholder="https://example.com",
                    id="scan-url",
                )
                yield Label("User Brief (optional):")
                yield Input(
                    placeholder="Describe what this app does...",
                    value=cfg.get("default_user_brief", ""),
                    id="scan-brief",
                )
                yield Label("Tech Stack (optional):")
                yield Input(
                    placeholder="React, Node.js, PostgreSQL...",
                    value=cfg.get("default_tech_stack", ""),
                    id="scan-tech",
                )
                yield Button("Start Scan", id="btn-start-scan", variant="primary")

            with Vertical(id="scan-progress-area"):
                yield Static("Ready to scan.", id="scan-progress-label")
                yield ProgressBar(total=100, show_eta=False, id="scan-progress-bar")
                yield Static("", id="scan-step-label")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start-scan" and not self._scanning:
            self._start_scan()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "scan-url" and not self._scanning:
            self._start_scan()

    def _start_scan(self) -> None:
        url = self.query_one("#scan-url", Input).value.strip()
        if not url:
            self.query_one("#scan-progress-label", Static).update(
                "[red]Please enter a URL.[/]"
            )
            return

        if not is_backend_available():
            self.query_one("#scan-progress-label", Static).update(
                "[red]Backend not available. Check installation.[/]"
            )
            return

        cfg = load_config()
        api_key = cfg.get("api_key", "")
        if not api_key:
            self.query_one("#scan-progress-label", Static).update(
                "[red]No API key set. Go to Settings [s] first.[/]"
            )
            return

        self._scanning = True
        self.query_one("#btn-start-scan", Button).disabled = True
        self.query_one("#scan-progress-label", Static).update("Creating scan...")

        brief = self.query_one("#scan-brief", Input).value.strip()
        tech = self.query_one("#scan-tech", Input).value.strip()
        llm_provider = cfg.get("llm_provider", "gemini")

        # Create scan record synchronously (DB call)
        self._scan_id = create_scan_record(
            url=url,
            user_brief=brief,
            tech_stack=tech,
        )

        # Launch the scan and progress tracking as workers
        self._run_scan_worker(self._scan_id, api_key, llm_provider)
        self._run_progress_worker(self._scan_id)

    @work(exclusive=True, thread=True)
    def _run_scan_worker(
        self, scan_id: str, api_key: str, llm_provider: str
    ) -> None:
        """Run the scan in a background thread with its own event loop."""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                launch_scan(
                    scan_id=scan_id,
                    api_key=api_key,
                    llm_provider=llm_provider,
                )
            )
        except Exception as exc:
            self.app.call_from_thread(
                self._on_scan_error, str(exc)
            )
        finally:
            loop.close()

    @work(exclusive=False, thread=True)
    def _run_progress_worker(self, scan_id: str) -> None:
        """Subscribe to progress events and update UI."""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._consume_progress(scan_id, loop))
        finally:
            loop.close()

    async def _consume_progress(self, scan_id: str, loop: asyncio.AbstractEventLoop) -> None:
        # Small delay to let the scan start and publish events
        await asyncio.sleep(0.5)

        async for event in subscribe_progress(scan_id):
            event_type = event.get("event", "")
            raw_data = event.get("data", "{}")

            try:
                data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
            except json.JSONDecodeError:
                data = {}

            if event_type == "progress":
                step = data.get("step", "")
                message = data.get("message", "")
                percent = data.get("percent", 0)
                self.app.call_from_thread(
                    self._update_progress, message, percent, step
                )

            elif event_type == "complete":
                self.app.call_from_thread(
                    self._on_scan_complete, scan_id
                )
                break

            elif event_type == "error":
                msg = data.get("message", "Unknown error")
                self.app.call_from_thread(
                    self._on_scan_error, msg
                )
                break

    def _update_progress(self, message: str, percent: int, step: str) -> None:
        self.query_one("#scan-progress-label", Static).update(message)
        self.query_one("#scan-progress-bar", ProgressBar).update(progress=percent)
        self.query_one("#scan-step-label", Static).update(f"[dim]{step}[/]")

    def _on_scan_complete(self, scan_id: str) -> None:
        self._scanning = False
        self.query_one("#scan-progress-label", Static).update(
            "[green]Scan complete![/]"
        )
        self.query_one("#scan-progress-bar", ProgressBar).update(progress=100)

        # Navigate to results
        from cli.screens.results import ResultsScreen
        self.app.push_screen(ResultsScreen(scan_id))

    def _on_scan_error(self, message: str) -> None:
        self._scanning = False
        self.query_one("#btn-start-scan", Button).disabled = False
        self.query_one("#scan-progress-label", Static).update(
            f"[red]Error: {message}[/]"
        )

    def action_go_back(self) -> None:
        if not self._scanning:
            self.app.pop_screen()
