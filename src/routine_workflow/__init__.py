# src/routine_workflow/__init__.py

"""Routine Workflow Package: Automates project hygiene tasks."""

from .cli import main  # CLI entrypoint

try:
    from importlib.metadata import version
    __version__ = version("routine-workflow")
except ImportError:
    # Fallback for pre-3.8 or non-installed envs (rare)
    import subprocess
    import sys
    try:
        # Git describe for dev (editable installs)
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
        )
        __version__ = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        __version__ = "dev"  # Ultimate fallback

__all__ = ["main"]