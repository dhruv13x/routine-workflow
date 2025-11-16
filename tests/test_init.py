# tests/test_init.py

"""Tests for __init__.py (version fetching and exports)."""

import importlib
import sys
from unittest.mock import patch, Mock
import pytest

sys.path.insert(0, 'src')  # Ensure import
import routine_workflow  # Initial load to define module


def test_version_installed():
    """Test __version__ from importlib.metadata in installed env."""
    with patch('importlib.metadata.version') as mock_version:
        mock_version.return_value = "6.4.4"
        importlib.reload(routine_workflow)  # Re-execute top-level with patch
        assert routine_workflow.__version__ == "6.4.4"


@patch('subprocess.run')  # Global patch for local import
def test_version_git_fallback(mock_run):
    """Test __version__ from git describe in dev env."""
    mock_run.return_value = Mock(returncode=0, stdout="v6.4.4\n")  # str for text=True match
    with patch.dict(sys.modules, {'importlib.metadata': None}):  # Force ImportError on metadata import
        importlib.reload(routine_workflow)  # Re-execute to hit fallback
    assert routine_workflow.__version__ == "v6.4.4"  # strip() removes \n


@patch('subprocess.run')  # Global patch for local import
def test_version_dev_fallback(mock_run):
    """Test ultimate 'dev' fallback on subprocess failure."""
    mock_run.side_effect = FileNotFoundError("No git")  # Matches except clause
    with patch.dict(sys.modules, {'importlib.metadata': None}):  # Force ImportError on metadata import
        importlib.reload(routine_workflow)  # Re-execute to hit fallback
    assert routine_workflow.__version__ == "dev"


def test_exports():
    """Test __all__ exports CLI entrypoint."""
    import routine_workflow
    assert routine_workflow.__all__ == ["main"]
