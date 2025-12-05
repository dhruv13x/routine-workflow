"""Configuration loader for pyproject.toml."""

import sys
from pathlib import Path
from typing import Any, Dict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_config(project_root: Path) -> Dict[str, Any]:
    """Load configuration from pyproject.toml in the project root.

    Returns a dictionary with keys normalized (dashes replaced by underscores).
    If the file or section doesn't exist, returns an empty dictionary.
    """
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        return {}

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        # If TOML is invalid, we probably want to warn, but for now just return empty
        # or let it crash if that's preferred. Usually robust tools warn and continue.
        # But here we'll assume valid TOML or fail.
        # Let's catch and print warning to stderr?
        # For simplicity, let's just propagate parse errors as they indicate user error.
        raise

    config_section = data.get("tool", {}).get("routine-workflow", {})

    # Normalize keys: kebab-case to snake_case
    normalized_config = {}
    for key, value in config_section.items():
        normalized_key = key.replace("-", "_")
        normalized_config[normalized_key] = value

    # print(f"DEBUG: Loaded config from {pyproject_path}: {normalized_config}", file=sys.stderr)
    return normalized_config
