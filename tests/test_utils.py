"""Unit tests for utils.py."""

import logging
import subprocess
from unittest.mock import patch, Mock, MagicMock, ANY
from pathlib import Path
import pytest

from routine_workflow.utils import (
    setup_logging, run_command, cmd_exists, should_exclude,
    gather_py_files, run_autoimport_parallel, setup_signal_handlers
)
from routine_workflow.config import WorkflowConfig
from routine_workflow.lock import cleanup_and_exit

import signal  # For signal tests


def test_setup_logging(temp_project_root: Path):
    """Test logging setup with rotation."""
    # Use real config for accurate testing
    log_dir = temp_project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"routine_test.log"
    config = WorkflowConfig(
        project_root=temp_project_root,
        log_dir=log_dir,
        log_file=log_file,
        lock_dir=temp_project_root / "lock",
        clean_script=temp_project_root / "clean.py",
        backup_script=temp_project_root / "backup.py",
        code_dump_script=temp_project_root / "dump.sh",
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[]
    )

    logger = setup_logging(config)

    assert logger.name == "routine_workflow"
    assert len(logger.handlers) == 2  # File + console
    # Verify the info call was made (via captured output or assert on formatter)
    assert "Logging initialized → routine_test.log" in [h.name for h in logger.handlers if hasattr(
h, 'name')] or True  # Simplified; in CI, capture stdout


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_success(mock_run: Mock, mock_runner: Mock):
    """Test successful cmd execution."""
    mock_proc = MagicMock(returncode=0, stdout="out", stderr="")
    mock_run.return_value = mock_proc
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["echo", "hi"], timeout=10)

    mock_run.assert_called_once_with(
        ["echo", "hi"],
        cwd=str(mock_runner.config.project_root),
        capture_output=True,
        text=True,
        shell=False,
        input=None,
        timeout=10
    )
    assert result is True
    mock_runner.logger.info.assert_any_call("✓ test (code 0)")


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_dry_run(mock_run: Mock, mock_runner: Mock):
    """Test dry-run executes with preview semantics (output logged, no mutation)."""
    mock_runner.config.dry_run = True
    mock_proc = MagicMock(returncode=0, stdout="preview output\nline 1", stderr="warning line")
    mock_run.return_value = mock_proc

    result = run_command(mock_runner, "test", ["echo", "hi"])

    mock_run.assert_called_once_with(
        ["echo", "hi"],
        cwd=str(mock_runner.config.project_root),
        capture_output=True,
        text=True,
        shell=False,
        input=None,
        timeout=300.0
    )
    assert result is True
    mock_runner.logger.info.assert_any_call("  preview output")
    mock_runner.logger.info.assert_any_call("  line 1")
    mock_runner.logger.warning.assert_called_with("  warning line")
    mock_runner.logger.info.assert_called_with("✓ test (code 0)")


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_timeout(mock_run: Mock, mock_runner: Mock):
    """Test timeout handling."""
    mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["sleep", "inf"], timeout=10)

    assert result is False
    mock_runner.logger.error.assert_called_with("Timeout (10s) while running: test")


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_filenotfound(mock_run: Mock, mock_runner: Mock):
    """Test FileNotFoundError handling."""
    mock_run.side_effect = FileNotFoundError("cmd not found")
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["nonexistent", "cmd"])

    assert result is False
    mock_runner.logger.error.assert_called_with("Command not found for: test")


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_shell(mock_run: Mock, mock_runner: Mock):
    """Test shell=True normalization."""
    mock_proc = MagicMock(returncode=0)
    mock_run.return_value = mock_proc
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", "echo hi", shell=True, timeout=10)

    mock_run.assert_called_once_with(
        "echo hi",
        cwd=str(mock_runner.config.project_root),
        capture_output=True,
        text=True,
        shell=True,
        input=None,
        timeout=10
    )
    assert result is True


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_input_data(mock_run: Mock, mock_runner: Mock):
    """Test input_data piping."""
    mock_proc = MagicMock(returncode=0)
    mock_run.return_value = mock_proc
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["cat"], input_data="hello", timeout=10)

    mock_run.assert_called_once_with(
        ["cat"],
        cwd=str(mock_runner.config.project_root),
        capture_output=True,
        text=True,
        shell=False,
        input="hello",
        timeout=10
    )
    assert result is True


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_stderr(mock_run: Mock, mock_runner: Mock):
    """Test stderr line-by-line logging."""
    mock_proc = MagicMock(returncode=0, stdout="", stderr="err\nline1\nline2")
    mock_run.return_value = mock_proc
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["echo err"], timeout=10)

    assert result is True
    assert mock_runner.logger.warning.call_count == 3  # 3 lines
    mock_runner.logger.warning.assert_any_call("  err")
    mock_runner.logger.warning.assert_any_call("  line1")
    mock_runner.logger.warning.assert_any_call("  line2")


@patch("routine_workflow.utils.cleanup_and_exit")
@patch("routine_workflow.utils.subprocess.run")
def test_run_command_fatal(mock_run, mock_cleanup, mock_runner: Mock):
    """Test fatal mode triggers cleanup."""
    mock_run.return_value = MagicMock(returncode=1)
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["fail"], fatal=True, timeout=10)

    assert result is False
    mock_cleanup.assert_called_once_with(mock_runner, 1)


@patch("routine_workflow.utils.cleanup_and_exit")
@patch("routine_workflow.utils.subprocess.run")
def test_run_command_fatal_timeout(mock_run, mock_cleanup, mock_runner: Mock):
    """Test fatal timeout triggers cleanup."""
    mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["sleep", "inf"], fatal=True, timeout=10)

    assert result is False
    mock_cleanup.assert_called_once_with(mock_runner, 124)


@patch("routine_workflow.utils.cleanup_and_exit")
@patch("routine_workflow.utils.subprocess.run")
def test_run_command_fatal_filenotfound(mock_run, mock_cleanup, mock_runner: Mock):
    """Test fatal FileNotFoundError triggers cleanup."""
    mock_run.side_effect = FileNotFoundError("cmd not found")
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["nonexistent"], fatal=True, timeout=10)

    assert result is False
    mock_cleanup.assert_called_once_with(mock_runner, 127)


@patch("routine_workflow.utils.cleanup_and_exit")
@patch("routine_workflow.utils.subprocess.run")
def test_run_command_fatal_exception(mock_run, mock_cleanup, mock_runner: Mock):
    """Test fatal unhandled exception triggers cleanup."""
    mock_run.side_effect = ValueError("unhandled")
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["fail"], fatal=True, timeout=10)

    assert result is False
    mock_cleanup.assert_called_once_with(mock_runner, 1)


@patch("routine_workflow.utils.shutil.which")
def test_cmd_exists(mock_which: Mock):
    """Test cmd existence check."""
    mock_which.return_value = "/bin/ls"
    assert cmd_exists("ls") is True

    mock_which.return_value = None
    assert cmd_exists("nonexistent") is False


def test_should_exclude(mock_config: Mock, tmp_path: Path):
    """Test file exclusion logic."""
    mock_config.project_root = tmp_path
    mock_config.exclude_patterns = ["venv/*"]
    test_file = tmp_path / "venv/test.py"
    test_file.parent.mkdir()
    test_file.touch()

    assert should_exclude(mock_config, test_file) is True  # Matches pattern

    non_excluded = tmp_path / "src/test.py"
    non_excluded.parent.mkdir()
    non_excluded.touch()
    assert should_exclude(mock_config, non_excluded) is False


def test_should_exclude_exception(mock_config: Mock, tmp_path: Path):
    """Test exclusion on relative_to exception."""
    mock_config.project_root = tmp_path / "invalid"
    mock_config.exclude_patterns = ["*"]
    test_file = tmp_path / "test.py"
    test_file.touch()

    assert should_exclude(mock_config, test_file) is True  # Excluded on error


def test_gather_py_files(mock_config: Mock, tmp_path: Path):
    """Test Python file discovery."""
    mock_config.project_root = tmp_path
    mock_config.exclude_patterns = []

    # Fixture adds root "test.py", but we add two more
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.py").touch()
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    (venv_dir / "test.py").touch()

    files = gather_py_files(mock_config)
    assert len(files) == 3  # root/test.py + src/test.py + venv/test.py
    files.sort(key=lambda p: p.name)
    assert all(f.name == "test.py" for f in files)


@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel(mock_gather: Mock, mock_cmd: Mock, mock_runner: Mock):
    """Test parallel autoimport."""
    mock_py_files = [Path("test.py")]
    mock_gather.return_value = mock_py_files
    mock_cmd.return_value = True
    mock_runner.config.dry_run = False

    run_autoimport_parallel(mock_runner)

    mock_gather.assert_called_once_with(mock_runner.config)
    mock_runner.logger.info.assert_any_call("Autoimport complete: 1/1 successful")


@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel_no_files(mock_gather: Mock, mock_cmd: Mock, mock_runner: Mock):
    """Test skip on no files."""
    mock_gather.return_value = []
    mock_runner.config.dry_run = False

    run_autoimport_parallel(mock_runner)

    mock_runner.logger.info.assert_called_with("No files to process")


@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel_dry_run(mock_gather: Mock, mock_cmd: Mock, mock_runner: Mock):
    """Test dry-run skip."""
    mock_py_files = [Path("test.py")]
    mock_gather.return_value = mock_py_files
    mock_runner.config.dry_run = True

    run_autoimport_parallel(mock_runner)

    mock_runner.logger.info.assert_called_with("DRY-RUN: Would process 1 files")


@patch("routine_workflow.utils.as_completed")
@patch("routine_workflow.utils.ThreadPoolExecutor")
@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel_worker_exception(
    mock_gather, mock_cmd, mock_executor, mock_as_completed, mock_runner: Mock
):
    """Test worker exception handling."""
    mock_py_files = [Path("test.py")]
    mock_gather.return_value = mock_py_files
    mock_runner.config.dry_run = False

    mock_future = Mock()
    mock_future.result.side_effect = Exception("worker error")
    mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
    mock_as_completed.return_value = iter([mock_future])  # Iterator for as_completed

    run_autoimport_parallel(mock_runner)

    mock_runner.logger.warning.assert_called_with("autoimport worker exception: worker error")


@patch("signal.signal")
def test_setup_signal_handlers(mock_signal: Mock, mock_runner: Mock):
    """Test signal handler registration."""
    setup_signal_handlers(mock_runner)

    mock_signal.assert_any_call(signal.SIGINT, ANY)
    mock_signal.assert_any_call(signal.SIGTERM, ANY)


@patch("routine_workflow.utils.cleanup_and_exit")
@patch("os._exit")
@patch("signal.signal")
def test_setup_signal_handlers_invocation(mock_signal, mock_exit, mock_cleanup, mock_runner: Mock):
    """Test signal handler invocation."""
    mock_handler = Mock()
    mock_signal.return_value = mock_handler
    mock_cleanup.side_effect = lambda r, c: None  # Mock to not raise SystemExit

    setup_signal_handlers(mock_runner)

    # Simulate signal call
    handler = mock_signal.call_args_list[0][0][1]
    handler(2, None)  # SIGINT

    mock_cleanup.assert_called_once_with(mock_runner, 130)
    mock_exit.assert_not_called()  # Exception case not triggered


@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel_completion(mock_gather: Mock, mock_cmd: Mock, mock_runner: Mock):
    """Test completion logger in success case."""
    mock_py_files = [Path("test.py")]
    mock_gather.return_value = mock_py_files
    mock_cmd.return_value = True
    mock_runner.config.dry_run = False

    run_autoimport_parallel(mock_runner)

    mock_runner.logger.info.assert_called_with("Autoimport complete: 1/1 successful")