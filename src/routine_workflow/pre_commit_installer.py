
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

def install_pre_commit_hook(project_root: Path) -> None:
    """Install or update .pre-commit-config.yaml with routine-workflow hook."""

    try:
        import yaml
    except ImportError:
        print("Error: PyYAML is required for pre-commit installation.", file=sys.stderr)
        print("Please install it via 'pip install pyyaml' or 'pip install routine-workflow[dev]'.", file=sys.stderr)
        sys.exit(1)

    config_path = project_root / ".pre-commit-config.yaml"

    # Define our hook config
    # We use 'local' repo because we assume routine-workflow is installed in the environment
    # or accessible.

    hook_config = {
        "repo": "local",
        "hooks": [
            {
                "id": "routine-workflow",
                "name": "routine-workflow",
                "entry": "routine-workflow",
                "language": "system",
                "pass_filenames": False,
                "always_run": True,
                # "args": ["--no-dry-run", "--yes"] # Optional: we can add args if needed, but user can customize
            }
        ]
    }

    current_config: Dict[str, Any] = {"repos": []}

    if config_path.exists():
        print(f"Updating existing {config_path}...")
        try:
            with open(config_path, "r") as f:
                loaded = yaml.safe_load(f)
                if loaded and isinstance(loaded, dict):
                    current_config = loaded
                else:
                    # If empty or invalid, we start fresh but warn
                    print("Warning: Existing config was empty or invalid. overwriting.")
        except Exception as e:
             print(f"Error reading existing config: {e}", file=sys.stderr)
             sys.exit(1)
    else:
        print(f"Creating new {config_path}...")

    if "repos" not in current_config:
        current_config["repos"] = []

    # Check if we already exist in local repo
    # We look for a repo with repo: local
    local_repo_index = -1
    for i, repo in enumerate(current_config["repos"]):
        if repo.get("repo") == "local":
            local_repo_index = i
            break

    if local_repo_index == -1:
        # Add new local repo block
        current_config["repos"].append(hook_config)
    else:
        # Update existing local repo block
        local_repo = current_config["repos"][local_repo_index]
        if "hooks" not in local_repo:
            local_repo["hooks"] = []

        # Check if hook id exists
        hook_exists = False
        for hook in local_repo["hooks"]:
            if hook.get("id") == "routine-workflow":
                hook_exists = True
                print("Hook 'routine-workflow' already exists. Skipping.")
                break

        if not hook_exists:
            local_repo["hooks"].append(hook_config["hooks"][0])
            print("Added 'routine-workflow' hook to existing local repo block.")

    # Write back
    try:
        with open(config_path, "w") as f:
            yaml.dump(current_config, f, sort_keys=False)
        print("✅ Pre-commit hook installed successfully.")
    except Exception as e:
        print(f"Error writing config: {e}", file=sys.stderr)
        sys.exit(1)
