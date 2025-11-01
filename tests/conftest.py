"""Pytest fixtures for routine_workflow."""

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Fix for src layout: Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from routine_workflow.config import WorkflowConfig
from routine_workflow.runner import WorkflowRunner


@pytest.fixture(autouse=True)
def setup_src_path():
    """Auto-add src to PYTHONPATH."""
    if 'src' not in sys.path:
        sys.path.insert(0, 'src')
    yield
    if sys.path and sys.path[0] == 'src':
        sys.path.pop(0)


@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Temporary project root for file ops."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "test.py").touch()  # Sample file
    return root


@pytest.fixture
def mock_config(temp_project_root: Path) -> Mock:
    """Mocked config with temp paths (mutable for tests; full Path mocks)."""
    config = Mock(spec=WorkflowConfig)
    
    # Core attrs as real Paths where no mocking needed
    config.project_root = temp_project_root
    config.log_dir = temp_project_root / "logs"
    config.log_dir.mkdir(exist_ok=True)
    config.log_file = config.log_dir / f"routine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    config.clean_script = temp_project_root / "clean.py"
    config.backup_script = temp_project_root / "backup.py"
    config.code_dump_script = temp_project_root / "dump.sh"
    
    # Mock lock_dir fully (avoids read-only Path methods)
    mock_lock_dir = Mock()
    mock_lock_dir.mkdir = Mock()
    mock_lock_dir.exists.return_value = False
    config.lock_dir = mock_lock_dir
    
    # Mock pid_path for release_lock
    mock_pid_path = Mock()
    mock_pid_path.write_text = Mock()
    mock_pid_path.read_text.return_value = str(os.getpid())
    mock_pid_path.exists.return_value = True
    mock_lock_dir.__truediv__ = lambda self, name: mock_pid_path if name == 'pid' else Mock()
    
    # Other attrs
    config.fail_on_backup = False
    config.auto_yes = False
    config.dry_run = True
    config.max_workers = min(8, os.cpu_count() or 4)
    config.workflow_timeout = 0
    config.exclude_patterns = []

    return config


@pytest.fixture
def mock_runner(mock_config: Mock) -> Mock:
    """Mock WorkflowRunner with logger and config."""
    runner = Mock(spec=WorkflowRunner)
    runner.config = mock_config
    runner.logger = Mock()
    runner._lock_acquired = False
    runner._pid_path = None
    return runner


@pytest.fixture
def mock_args() -> Mock:
    """Full mocked CLI args."""
    args = Mock()
    args.project_root = Path('/tmp/test')
    args.log_dir = Path('/tmp/logs')
    args.log_file = None
    args.lock_dir = Path('/tmp/lock')
    args.clean_script = Path('/tmp/clean.py')
    args.backup_script = Path('/tmp/backup.py')
    args.code_dump_sh = Path('/tmp/dump.sh')
    args.fail_on_backup = False
    args.yes = False
    args.dry_run = True
    args.workers = 4
    args.workflow_timeout = 0  # int
    args.exclude_patterns = None  # Trigger default
    return args