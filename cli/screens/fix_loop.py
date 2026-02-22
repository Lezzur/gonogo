"""GoNoGo TUI — Fix loop configuration and progress screen."""

import asyncio
import json

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Input, Label, ProgressBar, Select, Static
from textual import work

from cli.config import load_config
from cli.backend_bridge import (
    is_backend_available,
    get_scan,
    get_fix_cycles,
    launch_fix_loop,
    subscribe_progress,
)


class FixLoopScreen(Screen):
    """Fix loop config form + cycle progress display."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, scan_id: str) -> None:
        super().__init__()
        self.scan_id = scan_id
        self._running = False
        self._scan_data: dict = {}

    def on_mount(self) -> None:
        self._scan_data = get_scan(self.scan_id) or {}
        url = self._scan_data.get("url", "Unknown")
        verdict = self._scan_data.get("verdict", "?")
        score = self._scan_data.get("overall_score", "?")
        self.query_one("#fixloop-scan-info", Static).update(
            f"Scan: [bold]{url}[/]  |  Verdict: {verdict}  |  Score: {score}"
        )

    def compose(self) -> ComposeResult:
        cfg = load_config()
        fl = cfg.get("fix_loop", {})

        with Container(id="fixloop-container"):
            yield Static("[bold]Fix Loop[/bold]", id="fixloop-title")
            yield Static("", id="fixloop-scan-info")

            with Vertical(id="fixloop-config"):
                yield Static(
                    "[bold]Configuration[/bold]", classes="settings-section-title"
                )

                yield Label("Repository Path:")
                yield Input(
                    value=cfg.get("default_repo_path", ""),
                    placeholder="/path/to/your/project",
                    id="fl-repo-path",
                )

                yield Label("Max Cycles:")
                yield Input(
                    value=str(fl.get("max_cycles", 3)),
                    placeholder="3",
                    id="fl-max-cycles",
                )

                yield Label("Stop Condition:")
                yield Select(
                    options=[
                        ("GO", "GO"),
                        ("GO with Conditions", "GO_WITH_CONDITIONS"),
                        ("Never", "never"),
                    ],
                    value=fl.get("stop_condition", "GO"),
                    id="fl-stop-condition",
                )

                yield Label("Apply Mode:")
                yield Select(
                    options=[
                        ("Branch (safe)", "branch"),
                        ("Direct", "direct"),
                    ],
                    value=fl.get("apply_mode", "branch"),
                    id="fl-apply-mode",
                )

                yield Label("Deploy Mode:")
                yield Select(
                    options=[
                        ("Preview", "preview"),
                        ("Branch", "branch"),
                        ("Manual", "manual"),
                        ("Local", "local"),
                    ],
                    value=fl.get("deploy_mode", "preview"),
                    id="fl-deploy-mode",
                )

                yield Label("Deploy Command:")
                yield Input(
                    value=fl.get("deploy_command", ""),
                    placeholder="vercel deploy --branch {branch}",
                    id="fl-deploy-command",
                )

                yield Label("Severity Filter:")
                yield Input(
                    value=", ".join(fl.get("severity_filter", ["critical", "high", "medium", "low"])),
                    placeholder="critical, high, medium, low",
                    id="fl-severity-filter",
                )

                with Horizontal():
                    yield Button(
                        "Start Fix Loop",
                        id="btn-start-fixloop",
                        variant="primary",
                    )

            with Vertical(id="fixloop-progress-area"):
                yield Static("Ready.", id="fixloop-progress-label")
                yield ProgressBar(
                    total=100, show_eta=False, id="fixloop-progress-bar"
                )
                yield Static("", id="fixloop-step-label")

            yield Static("", id="fixloop-cycles")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start-fixloop" and not self._running:
            self._start_fix_loop()

    def _start_fix_loop(self) -> None:
        repo_path = self.query_one("#fl-repo-path", Input).value.strip()
        if not repo_path:
            self.query_one("#fixloop-progress-label", Static).update(
                "[red]Repository path is required.[/]"
            )
            return

        if not is_backend_available():
            self.query_one("#fixloop-progress-label", Static).update(
                "[red]Backend not available.[/]"
            )
            return

        cfg = load_config()
        api_key = cfg.get("api_key", "")
        if not api_key:
            self.query_one("#fixloop-progress-label", Static).update(
                "[red]No API key set. Go to Settings [s].[/]"
            )
            return

        self._running = True
        self.query_one("#btn-start-fixloop", Button).disabled = True
        self.query_one("#fixloop-progress-label", Static).update(
            "Starting fix loop..."
        )

        try:
            max_cycles = int(self.query_one("#fl-max-cycles", Input).value.strip() or "3")
        except ValueError:
            max_cycles = 3

        stop_select = self.query_one("#fl-stop-condition", Select)
        apply_select = self.query_one("#fl-apply-mode", Select)
        deploy_select = self.query_one("#fl-deploy-mode", Select)

        def _sel(widget: Select, default: str) -> str:
            v = widget.value
            return v if isinstance(v, str) else default

        stop_condition = _sel(stop_select, "GO")
        apply_mode = _sel(apply_select, "branch")
        deploy_mode = _sel(deploy_select, "preview")
        deploy_command = self.query_one("#fl-deploy-command", Input).value.strip()

        severity_raw = self.query_one("#fl-severity-filter", Input).value.strip()
        severity_filter = [s.strip() for s in severity_raw.split(",") if s.strip()]

        llm_provider = cfg.get("llm_provider", "gemini")

        self._run_fixloop_worker(
            repo_path,
            api_key,
            llm_provider,
            max_cycles,
            str(stop_condition),
            str(apply_mode),
            str(deploy_mode),
            deploy_command,
            severity_filter,
        )
        self._run_fixloop_progress_worker()

    @work(exclusive=True, thread=True)
    def _run_fixloop_worker(
        self,
        repo_path: str,
        api_key: str,
        llm_provider: str,
        max_cycles: int,
        stop_on_verdict: str,
        apply_mode: str,
        deploy_mode: str,
        deploy_command: str,
        severity_filter: list[str],
    ) -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                launch_fix_loop(
                    scan_id=self.scan_id,
                    repo_path=repo_path,
                    api_key=api_key,
                    llm_provider=llm_provider,
                    max_cycles=max_cycles,
                    stop_on_verdict=stop_on_verdict,
                    apply_mode=apply_mode,
                    deploy_mode=deploy_mode,
                    deploy_command=deploy_command,
                    severity_filter=severity_filter,
                )
            )
        except Exception as exc:
            self.app.call_from_thread(self._on_fixloop_error, str(exc))
        finally:
            loop.close()

    @work(exclusive=False, thread=True)
    def _run_fixloop_progress_worker(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._consume_fixloop_progress(loop))
        finally:
            loop.close()

    async def _consume_fixloop_progress(self, loop: asyncio.AbstractEventLoop) -> None:
        await asyncio.sleep(0.5)

        async for event in subscribe_progress(self.scan_id):
            event_type = event.get("event", "")
            raw_data = event.get("data", "{}")

            try:
                data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
            except json.JSONDecodeError:
                data = {}

            if event_type == "progress":
                message = data.get("message", "")
                percent = data.get("percent", 0)
                step = data.get("step", "")
                self.app.call_from_thread(
                    self._update_fixloop_progress, message, percent, step
                )
            elif event_type == "complete":
                self.app.call_from_thread(self._on_fixloop_complete)
                break
            elif event_type == "error":
                msg = data.get("message", "Unknown error")
                self.app.call_from_thread(self._on_fixloop_error, msg)
                break

    def _update_fixloop_progress(
        self, message: str, percent: int, step: str
    ) -> None:
        self.query_one("#fixloop-progress-label", Static).update(message)
        self.query_one("#fixloop-progress-bar", ProgressBar).update(progress=percent)
        self.query_one("#fixloop-step-label", Static).update(f"[dim]{step}[/]")

        # Refresh cycle data
        self._refresh_cycles()

    def _on_fixloop_complete(self) -> None:
        self._running = False
        self.query_one("#fixloop-progress-label", Static).update(
            "[green]Fix loop complete![/]"
        )
        self.query_one("#fixloop-progress-bar", ProgressBar).update(progress=100)
        self._refresh_cycles()

    def _on_fixloop_error(self, message: str) -> None:
        self._running = False
        self.query_one("#btn-start-fixloop", Button).disabled = False
        self.query_one("#fixloop-progress-label", Static).update(
            f"[red]Error: {message}[/]"
        )

    def _refresh_cycles(self) -> None:
        cycles = get_fix_cycles(self.scan_id)
        if not cycles:
            return

        lines = ["[bold]Cycles:[/bold]"]
        for c in cycles:
            num = c["cycle_number"]
            status = c["status"]
            resolved = c["findings_resolved"]
            new = c["findings_new"]
            cost = c.get("cost_usd")
            cost_str = f"${cost:.2f}" if cost else "--"

            status_color = {
                "completed": "green",
                "failed": "red",
                "fixing": "yellow",
                "deploying": "cyan",
                "rescanning": "blue",
            }.get(status, "white")

            lines.append(
                f"  Cycle {num}: [{status_color}]{status}[/]  "
                f"| Resolved: {resolved}  | New: {new}  | Cost: {cost_str}"
            )

        self.query_one("#fixloop-cycles", Static).update("\n".join(lines))

    def action_go_back(self) -> None:
        if not self._running:
            self.app.pop_screen()
