"""GoNoGo TUI — User configuration (~/.gonogo/config.json)."""

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".gonogo"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "llm_provider": "gemini",
    "reports_save_path": str(Path.home() / "gonogo-reports"),
    "default_repo_path": "",
    "default_user_brief": "",
    "default_tech_stack": "",
    "fix_loop": {
        "max_cycles": 3,
        "stop_condition": "GO",
        "apply_mode": "branch",
        "permission_mode": "full",
        "deploy_mode": "preview",
        "deploy_command": "vercel deploy --branch {branch}",
        "local_dev_url": "http://localhost:3000",
        "severity_filter": ["critical", "high", "medium", "low"],
    },
}


def load_config() -> dict:
    """Load config from disk, merging with defaults for any missing keys."""
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_PATH, "r") as f:
            user_cfg = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)

    merged = dict(DEFAULT_CONFIG)
    merged.update(user_cfg)

    # Deep-merge fix_loop sub-dict
    default_fl = dict(DEFAULT_CONFIG["fix_loop"])
    user_fl = user_cfg.get("fix_loop", {})
    if isinstance(user_fl, dict):
        default_fl.update(user_fl)
    merged["fix_loop"] = default_fl

    return merged


def save_config(cfg: dict) -> None:
    """Write config to ~/.gonogo/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def get_value(key: str, default: Any = None) -> Any:
    """Get a single config value by dot-notation key (e.g. 'fix_loop.max_cycles')."""
    cfg = load_config()
    parts = key.split(".")
    node = cfg
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node
