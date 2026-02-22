import re
from pathlib import Path
from typing import Dict, Any

_BACKEND_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = _BACKEND_DIR / "prompts" if (_BACKEND_DIR / "prompts").is_dir() else _BACKEND_DIR.parent / "prompts"


def load_prompt(prompt_name: str, version: str = None, **kwargs) -> str:
    """
    Load a prompt template and inject dynamic data.

    Args:
        prompt_name: Name of the prompt (e.g., "intent_analysis")
        version: Version suffix (e.g., "v1"). If None, uses latest version.
        **kwargs: Dynamic data to inject into {{placeholders}}

    Returns:
        Formatted prompt string
    """
    # Auto-detect latest version if not specified
    if version is None:
        version = get_prompt_version(prompt_name)

    filename = f"{prompt_name}_{version}.md"
    prompt_path = PROMPTS_DIR / filename

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Replace placeholders
    for key, value in kwargs.items():
        placeholder = f"{{{{{key}}}}}"
        if isinstance(value, (dict, list)):
            import json
            value = json.dumps(value, indent=2)
        template = template.replace(placeholder, str(value))

    return template


def get_prompt_version(prompt_name: str) -> str:
    """Get the latest version of a prompt template."""
    versions = []
    for file in PROMPTS_DIR.glob(f"{prompt_name}_v*.md"):
        match = re.search(r"_v(\d+)\.md$", file.name)
        if match:
            versions.append(int(match.group(1)))

    if not versions:
        return "v1"

    return f"v{max(versions)}"
