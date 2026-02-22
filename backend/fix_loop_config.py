"""
GoNoGo Fix Loop Configuration

Loads environment variables for the scan→fix→rescan automation cycle.
Import from this module in fix loop services — do not merge with config.py.
"""

import os


# ============================================================================
# CYCLE CONTROL
# ============================================================================

DEFAULT_MAX_CYCLES: int = int(os.getenv("DEFAULT_MAX_CYCLES", "3"))
"""Maximum number of scan→fix→rescan cycles before stopping."""

DEFAULT_STOP_ON_VERDICT: str = os.getenv("DEFAULT_STOP_ON_VERDICT", "GO")
"""
Auto-stop when this verdict is reached.
Valid values: "GO", "GO_WITH_CONDITIONS", "never"
- "GO": Stop when verdict reaches GO
- "GO_WITH_CONDITIONS": Stop when verdict reaches GO_WITH_CONDITIONS or better
- "never": Run all cycles regardless of verdict (manual stop only)
"""


# ============================================================================
# DEPLOYMENT & FIX APPLICATION
# ============================================================================

DEFAULT_DEPLOY_MODE: str = os.getenv("DEFAULT_DEPLOY_MODE", "branch")
"""
How to deploy fixes for testing.
- "branch": Create new branch per cycle, deploy that
- "main": Deploy to main branch (not recommended)
- "pr": Create PR per cycle
"""

DEFAULT_APPLY_MODE: str = os.getenv("DEFAULT_APPLY_MODE", "branch")
"""
How to apply fixes to codebase.
- "branch": Apply fixes to new branch
- "main": Apply directly to main branch (dangerous)
- "commit": Create commits on current branch
"""

FIX_BRANCH_PREFIX: str = os.getenv("FIX_BRANCH_PREFIX", "gonogo/fix-")
"""Prefix for auto-generated fix branches. Example: gonogo/fix-cycle-1"""


# ============================================================================
# CLAUDE CODE INTEGRATION
# ============================================================================

CLAUDE_CODE_PATH: str = os.getenv("CLAUDE_CODE_PATH", "claude")
"""
Path to Claude Code CLI binary.
Default "claude" assumes it's in PATH. Use full path if needed.
Example: "/usr/local/bin/claude" or "C:\\Program Files\\Claude\\claude.exe"
"""

CLAUDE_CODE_MAX_TURNS: int = int(os.getenv("CLAUDE_CODE_MAX_TURNS", "50"))
"""
Maximum number of tool-use turns per fix session.
50 turns is usually enough for moderate complexity fixes.
"""

CLAUDE_CODE_TIMEOUT_SECONDS: int = int(os.getenv("CLAUDE_CODE_TIMEOUT_SECONDS", "600"))
"""Timeout per fix session in seconds. Default: 600 (10 minutes)"""

CLAUDE_CODE_PERMISSION_MODE: str = os.getenv(
    "CLAUDE_CODE_PERMISSION_MODE", "bypassPermissions"
)
"""
Claude Code permission mode.
- "bypassPermissions": Full automation, relies on git branch for safety (RECOMMENDED)
- "acceptEdits": More cautious, may cause incomplete fixes for bash-heavy operations.
"""

CLAUDE_CODE_ALLOWED_TOOLS: str = os.getenv(
    "CLAUDE_CODE_ALLOWED_TOOLS",
    "Read,Write,Edit,Bash(npm run *),Bash(npx *),Bash(git diff *),Bash(git status)",
)
"""
Allowed tools when CLAUDE_CODE_PERMISSION_MODE is not "bypassPermissions".
Ignored when bypassPermissions is active.
"""

CLAUDE_CODE_MAX_BUDGET_USD: float = float(os.getenv("CLAUDE_CODE_MAX_BUDGET_USD", "5.0"))
"""Maximum budget per cycle in USD. Default: $5.00"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_config_summary() -> dict:
    """Return a dictionary of all fix loop configuration values for debugging."""
    return {
        "cycle_control": {
            "max_cycles": DEFAULT_MAX_CYCLES,
            "stop_on_verdict": DEFAULT_STOP_ON_VERDICT,
        },
        "deployment": {
            "deploy_mode": DEFAULT_DEPLOY_MODE,
            "apply_mode": DEFAULT_APPLY_MODE,
            "fix_branch_prefix": FIX_BRANCH_PREFIX,
        },
        "claude_code": {
            "path": CLAUDE_CODE_PATH,
            "max_turns": CLAUDE_CODE_MAX_TURNS,
            "timeout_seconds": CLAUDE_CODE_TIMEOUT_SECONDS,
            "permission_mode": CLAUDE_CODE_PERMISSION_MODE,
            "allowed_tools": CLAUDE_CODE_ALLOWED_TOOLS,
            "max_budget_usd": CLAUDE_CODE_MAX_BUDGET_USD,
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_config_summary(), indent=2))
