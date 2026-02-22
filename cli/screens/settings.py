"""GoNoGo TUI — Settings screen for config management."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Input, Label, Select, Static

from cli.config import load_config, save_config


class SettingsScreen(Screen):
    """Config form: API key, LLM provider, paths, fix loop defaults."""

    BINDINGS = [("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        cfg = load_config()
        fl = cfg.get("fix_loop", {})

        with Container(id="settings-container"):
            yield Static("[bold]Settings[/bold]", id="settings-title")

            # General section
            with Vertical(classes="settings-section"):
                yield Static("[bold]General[/bold]", classes="settings-section-title")

                yield Label("API Key:")
                yield Input(
                    value=cfg.get("api_key", ""),
                    password=True,
                    placeholder="Your Gemini or Anthropic API key",
                    id="cfg-api-key",
                )

                yield Label("LLM Provider:")
                yield Select(
                    options=[
                        ("Gemini", "gemini"),
                        ("Claude", "claude"),
                    ],
                    value=cfg.get("llm_provider", "gemini"),
                    id="cfg-llm-provider",
                )

                yield Label("Reports Save Path:")
                yield Input(
                    value=cfg.get("reports_save_path", ""),
                    placeholder="~/gonogo-reports",
                    id="cfg-reports-path",
                )

            # Defaults section
            with Vertical(classes="settings-section"):
                yield Static(
                    "[bold]Scan Defaults[/bold]", classes="settings-section-title"
                )

                yield Label("Default Repo Path:")
                yield Input(
                    value=cfg.get("default_repo_path", ""),
                    placeholder="/path/to/your/project",
                    id="cfg-repo-path",
                )

                yield Label("Default User Brief:")
                yield Input(
                    value=cfg.get("default_user_brief", ""),
                    placeholder="What the app does...",
                    id="cfg-user-brief",
                )

                yield Label("Default Tech Stack:")
                yield Input(
                    value=cfg.get("default_tech_stack", ""),
                    placeholder="React, Node.js...",
                    id="cfg-tech-stack",
                )

            # Fix loop section
            with Vertical(classes="settings-section"):
                yield Static(
                    "[bold]Fix Loop Defaults[/bold]",
                    classes="settings-section-title",
                )

                yield Label("Max Cycles:")
                yield Input(
                    value=str(fl.get("max_cycles", 3)),
                    placeholder="3",
                    id="cfg-fl-max-cycles",
                )

                yield Label("Stop Condition:")
                yield Select(
                    options=[
                        ("GO", "GO"),
                        ("GO with Conditions", "GO_WITH_CONDITIONS"),
                        ("Never (run all cycles)", "never"),
                    ],
                    value=fl.get("stop_condition", "GO"),
                    id="cfg-fl-stop-condition",
                )

                yield Label("Apply Mode:")
                yield Select(
                    options=[
                        ("Branch (safe)", "branch"),
                        ("Direct (risky)", "direct"),
                    ],
                    value=fl.get("apply_mode", "branch"),
                    id="cfg-fl-apply-mode",
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
                    id="cfg-fl-deploy-mode",
                )

                yield Label("Deploy Command:")
                yield Input(
                    value=fl.get("deploy_command", ""),
                    placeholder="vercel deploy --branch {branch}",
                    id="cfg-fl-deploy-command",
                )

                yield Label("Local Dev URL:")
                yield Input(
                    value=fl.get("local_dev_url", ""),
                    placeholder="http://localhost:3000",
                    id="cfg-fl-local-dev-url",
                )

            # Buttons
            with Horizontal(id="settings-buttons"):
                yield Button("Save", id="btn-save-settings", variant="primary")
                yield Button("Cancel", id="btn-cancel-settings", variant="default")

            yield Static("", id="settings-status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-settings":
            self._save()
        elif event.button.id == "btn-cancel-settings":
            self.app.pop_screen()

    def _save(self) -> None:
        try:
            max_cycles_str = self.query_one("#cfg-fl-max-cycles", Input).value.strip()
            max_cycles = int(max_cycles_str) if max_cycles_str else 3
        except ValueError:
            max_cycles = 3

        provider_select = self.query_one("#cfg-llm-provider", Select)
        stop_select = self.query_one("#cfg-fl-stop-condition", Select)
        apply_select = self.query_one("#cfg-fl-apply-mode", Select)
        deploy_select = self.query_one("#cfg-fl-deploy-mode", Select)

        def _sel(widget: Select, default: str) -> str:
            v = widget.value
            return v if isinstance(v, str) else default

        cfg = {
            "api_key": self.query_one("#cfg-api-key", Input).value.strip(),
            "llm_provider": _sel(provider_select, "gemini"),
            "reports_save_path": self.query_one("#cfg-reports-path", Input).value.strip(),
            "default_repo_path": self.query_one("#cfg-repo-path", Input).value.strip(),
            "default_user_brief": self.query_one("#cfg-user-brief", Input).value.strip(),
            "default_tech_stack": self.query_one("#cfg-tech-stack", Input).value.strip(),
            "fix_loop": {
                "max_cycles": max_cycles,
                "stop_condition": _sel(stop_select, "GO"),
                "apply_mode": _sel(apply_select, "branch"),
                "deploy_mode": _sel(deploy_select, "preview"),
                "deploy_command": self.query_one("#cfg-fl-deploy-command", Input).value.strip(),
                "local_dev_url": self.query_one("#cfg-fl-local-dev-url", Input).value.strip(),
                "severity_filter": ["critical", "high", "medium", "low"],
            },
        }

        save_config(cfg)
        self.query_one("#settings-status", Static).update(
            "[green]Settings saved![/]"
        )

    def action_go_back(self) -> None:
        self.app.pop_screen()
