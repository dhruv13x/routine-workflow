# tests/test_utils.py

"""Unit tests for utils.py."""

import sys
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
import os


from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import pytest
from logging import StreamHandler, Formatter

from routine_workflow.utils import setup_logging, run_command, RotatingFileHandler
from routine_workflow.config import WorkflowConfig


@pytest.fixture(autouse=True)
def clear_logger():
    """Clear logger handlers before each test to avoid persistence issues."""
    logger = logging.getLogger("routine_workflow")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    logger.handlers.clear()
    yield
    # No need to restore; fresh start each time


def test_setup_logging(temp_project_root: Path, capsys):
    """Test logging setup with rotation (Rich branch)."""
    # Use real config for accurate testing
    log_dir = temp_project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "routine_test.log"
    config = WorkflowConfig(
        project_root=temp_project_root,
        log_dir=log_dir,
        log_file=log_file,
        lock_dir=temp_project_root / "lock",
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[]
    )

    with patch('routine_workflow.utils._has_rich', return_value=True):
        with patch('rich.logging.RichHandler') as mock_rich_handler:
            mock_handler = Mock()
            mock_handler.level = 0  # Fix: Set level to int to pass logging comparison
            mock_rich_handler.return_value = mock_handler
            logger = setup_logging(config)

    assert logger.name == "routine_workflow"
    assert len(logger.handlers) == 2  # File + RichHandler
    # Verify RichHandler mock was instantiated with params
    mock_rich_handler.assert_called_once_with(show_level=True, show_path=False, omit_repeated_times=True)
    # Trigger a log to test handler emit (mocked, so no output, but verifies no crash)
    logger.info("Test log after setup")
    # Capture to confirm no unexpected output (mock doesn't print)
    captured = capsys.readouterr()
    assert "Test log after setup" not in captured.out  # Mocked, no print
    # Verify init log was called (via mock or captured if plain, but since Rich mocked, use mock side effect if needed)
    # Note: For full output test, use plain branch test separately


def test_setup_logging_plain(temp_project_root: Path, capsys):
    """Test logging setup with rotation (plain branch)."""
    log_dir = temp_project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "routine_test.log"
    config = WorkflowConfig(
        project_root=temp_project_root,
        log_dir=log_dir,
        log_file=log_file,
        lock_dir=temp_project_root / "lock",
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        # --- FIXED: Add missing fields ---
        lock_ttl=3600,
        create_dump_clean_cmd=[],
        create_dump_run_cmd=[],
        fail_on_backup=False,
        auto_yes=False,
        test_cov_threshold=85,
        git_push=False,
        enable_security=False,
        enable_dep_audit=False
    )

    with patch('routine_workflow.utils._has_rich', return_value=False):
        logger = setup_logging(config)

    assert logger.name == "routine_workflow"
    assert len(logger.handlers) == 2  # File + StreamHandler
    
    # --- FIXED: Find the console handler reliably ---
    # It's the StreamHandler that is NOT a RotatingFileHandler
    ch = next(h for h in logger.handlers if isinstance(h, StreamHandler) and not isinstance(h, RotatingFileHandler))
    
    assert isinstance(ch.formatter, Formatter)
    
    # Trigger log to test emit and capture output
    logger.info("Test log after setup")
    sys.stdout.flush()
    sys.stderr.flush()
    captured = capsys.readouterr()
    
    # --- FIXED: Remove brittle date check, assert message content ---
    assert "Test log after setup" in captured.err
    assert "INFO: Test log after setup" in captured.err


def test_setup_logging_rich(temp_project_root: Path):
    """Test logging setup with rotation (Rich branch)."""
    # Use real config for accurate testing
    log_dir = temp_project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "routine_test.log"
    config = WorkflowConfig(
        project_root=temp_project_root,
        log_dir=log_dir,
        log_file=log_file,
        lock_dir=temp_project_root / "lock",
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        create_dump_clean_cmd=[],  # Explicit list for defaults
        create_dump_run_cmd=[]  # Explicit list for defaults
    )

    with patch('routine_workflow.utils._has_rich', return_value=True):
        with patch('rich.logging.RichHandler') as mock_rich_handler:
            mock_handler = Mock()
            mock_handler.level = 0  # Skip level comparison error in logging
            mock_rich_handler.return_value = mock_handler
            logger = setup_logging(config)

    # Verify RichHandler mock was instantiated with params
    mock_rich_handler.assert_called_once_with(show_level=True, show_path=False, omit_repeated_times=True)
    assert len(logger.handlers) == 2  # File + RichHandler
    # Trigger log to test mock (no output, but verifies no crash)
    logger.info("Test log after setup")
    
    
@patch("routine_workflow.utils.subprocess.run")
@patch('routine_workflow.utils._has_rich', return_value=False)  # Force plain logging for test
def test_run_command_success(mock_has_rich, mock_run: Mock, mock_runner: Mock):
    """Test successful cmd execution."""
    mock_runner.config.dry_run = False
    mock_proc = MagicMock(returncode=0, stdout="out", stderr="")
    mock_run.return_value = mock_proc

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
    assert result["success"] is True  # Now passes since returncode=0 and no exceptions
    mock_runner.logger.info.assert_any_call("✓ test (code 0)")  # Verify success log
    

@patch("routine_workflow.utils.subprocess.run")
def test_run_command_dry_run(mock_run: Mock, mock_runner: Mock):
    """Test dry-run executes with preview semantics (output logged, no mutation)."""
    mock_runner.config.dry_run = True
    mock_proc = MagicMock(returncode=0, stdout="preview output\nline 1", stderr="warning line")
    mock_run.return_value = mock_proc

    with patch('routine_workflow.utils._has_rich', return_value=False):
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
    assert result["success"] is True
    mock_runner.logger.info.assert_any_call("  preview output")
    mock_runner.logger.info.assert_any_call("  line 1")
    mock_runner.logger.warning.assert_called_once_with("  warning line")
    mock_runner.logger.info.assert_called_with("✓ test (code 0)")


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_timeout(mock_run: Mock, mock_runner: Mock):
    """Test timeout handling."""
    mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["sleep", "inf"], timeout=10)

    assert result["success"] is False
    mock_runner.logger.error.assert_called_with("Timeout (10s) while running: test")


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_filenotfound(mock_run: Mock, mock_runner: Mock):
    """Test FileNotFoundError handling."""
    mock_run.side_effect = FileNotFoundError("cmd not found")
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["nonexistent", "cmd"])

    assert result["success"] is False
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
    assert result["success"] is True


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
    assert result["success"] is True


@patch('routine_workflow.utils._has_rich', return_value=False)
@patch('routine_workflow.utils.subprocess.run')
def test_run_command_stderr(mock_run: Mock, mock_runner: Mock):
    """Test stderr line-by-line logging."""
    mock_proc = MagicMock(returncode=0, stdout="", stderr="err\nline1\nline2")
    mock_run.return_value = mock_proc
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["echo err"], timeout=10)

    assert result["success"] is True
    assert mock_runner.logger.warning.call_count == 3  # 3 lines
    mock_runner.logger.warning.assert_any_call("  err")
    mock_runner.logger.warning.assert_any_call("  line1")
    mock_runner.logger.warning.assert_any_call("  line2")
    mock_runner.logger.info.assert_called_with("✓ test (code 0)")


@patch("routine_workflow.utils.cleanup_and_exit")
@patch("routine_workflow.utils.subprocess.run")
def test_run_command_fatal(mock_run, mock_cleanup, mock_runner: Mock):
    """Test fatal mode triggers cleanup."""
    mock_run.return_value = MagicMock(returncode=1)
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["fail"], fatal=True, timeout=10)

    assert result["success"] is False
    mock_cleanup.assert_called_once_with(mock_runner, 1)


@patch("routine_workflow.utils.cleanup_and_exit")
@patch("routine_workflow.utils.subprocess.run")
def test_run_command_fatal_timeout(mock_run, mock_cleanup, mock_runner: Mock):
    """Test fatal timeout triggers cleanup."""
    mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["sleep", "inf"], fatal=True, timeout=10)

    assert result["success"] is False
    mock_cleanup.assert_called_once_with(mock_runner, 124)


@patch("routine_workflow.utils.cleanup_and_exit")
@patch("routine_workflow.utils.subprocess.run")
def test_run_command_fatal_filenotfound(mock_run, mock_cleanup, mock_runner: Mock):
    """Test fatal FileNotFoundError triggers cleanup."""
    mock_run.side_effect = FileNotFoundError("cmd not found")
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["nonexistent"], fatal=True, timeout=10)

    assert result["success"] is False
    mock_cleanup.assert_called_once_with(mock_runner, 127)


@patch("routine_workflow.utils.cleanup_and_exit")
@patch("routine_workflow.utils.subprocess.run")
def test_run_command_fatal_exception(mock_run, mock_cleanup, mock_runner: Mock):
    """Test fatal unhandled exception triggers cleanup."""
    mock_run.side_effect = ValueError("unhandled")
    mock_runner.config.dry_run = False

    result = run_command(mock_runner, "test", ["fail"], fatal=True, timeout=10)

    assert result["success"] is False
    mock_cleanup.assert_called_once_with(mock_runner, 1)


@patch("routine_workflow.utils.threading.Thread")
@patch("routine_workflow.utils.subprocess.Popen")
@patch('routine_workflow.utils._has_rich', return_value=False)
def test_run_command_stream_success(mock_has_rich, mock_popen, mock_thread, mock_runner: Mock):
    """Test successful streaming of stdout and stderr."""
    mock_proc = MagicMock()
    mock_proc.stdout.readline.side_effect = ["out1\n", "out2\n", ""]
    mock_proc.stderr.readline.side_effect = ["err1\n", ""]
    mock_proc.wait.return_value = 0
    mock_popen.return_value = mock_proc

    # --- FIXED: Correct side_effect logic ---
    def thread_side_effect(target, args, daemon=None):
        thread_instance = MagicMock()
        thread_instance.start.side_effect = lambda: target(*args)
        return thread_instance
    mock_thread.side_effect = thread_side_effect

    result = run_command(mock_runner, "test stream", ["echo"], stream=True)

    assert result["success"] is True
    assert result["stdout"] == "" # Streamed, not captured
    assert result["stderr"] == "" # Streamed, not captured

    mock_popen.assert_called_once_with(
        ["echo"],
        cwd=str(mock_runner.config.project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=None,
        text=True,
        shell=False,
        bufsize=1,
        universal_newlines=True
    )
    
    # Check that logger was called with streamed output
    mock_runner.logger.info.assert_any_call("  out1")
    mock_runner.logger.info.assert_any_call("  out2")
    mock_runner.logger.warning.assert_any_call("  err1")
    mock_runner.logger.info.assert_any_call("✓ test stream (code 0)")


@patch("routine_workflow.utils.threading.Thread")
@patch("routine_workflow.utils.subprocess.Popen")
@patch('routine_workflow.utils._has_rich', return_value=False)
def test_run_command_stream_with_input(mock_has_rich, mock_popen, mock_thread, mock_runner: Mock):
    """Test streaming with input_data."""
    mock_proc = MagicMock()
    mock_proc.stdout.readline.side_effect = [""]
    mock_proc.stderr.readline.side_effect = [""]
    mock_proc.wait.return_value = 0
    mock_proc.stdin = MagicMock() # Mock stdin
    mock_popen.return_value = mock_proc
    
    # --- FIXED: Correct side_effect logic ---
    def thread_side_effect(target, args, daemon=None):
        thread_instance = MagicMock()
        thread_instance.start.side_effect = lambda: target(*args)
        return thread_instance
    mock_thread.side_effect = thread_side_effect

    result = run_command(mock_runner, "test stream", ["cat"], stream=True, input_data="hello")

    assert result["success"] is True
    mock_popen.assert_called_once_with(
        ["cat"],
        cwd=str(mock_runner.config.project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE, # stdin should be PIPE
        text=True,
        shell=False,
        bufsize=1,
        universal_newlines=True
    )
    
    # Check that stdin was written to and closed
    mock_proc.stdin.write.assert_called_once_with("hello")
    mock_proc.stdin.close.assert_called_once()


@patch("routine_workflow.utils.threading.Thread")
@patch("routine_workflow.utils.subprocess.Popen")
@patch('routine_workflow.utils._has_rich', return_value=False)
def test_run_command_stream_timeout(mock_has_rich, mock_popen, mock_thread, mock_runner: Mock):
    """Test streaming with a timeout."""
    mock_proc = MagicMock()
    mock_proc.stdout.readline.side_effect = [""]
    mock_proc.stderr.readline.side_effect = [""]
    mock_proc.wait.side_effect = subprocess.TimeoutExpired("cmd", 0.1)
    mock_popen.return_value = mock_proc
    
    # --- FIXED: Correct side_effect logic ---
    def thread_side_effect(target, args, daemon=None):
        thread_instance = MagicMock()
        thread_instance.start.side_effect = lambda: target(*args)
        return thread_instance
    mock_thread.side_effect = thread_side_effect

    result = run_command(mock_runner, "test stream", ["sleep", "10"], stream=True, timeout=0.1)

    assert result["success"] is False
    assert result["stdout"] == ""
    assert result["stderr"] == "" # The exception is no longer leaked to stderr

    mock_proc.wait.assert_called_once_with(timeout=0.1)
    mock_proc.kill.assert_called_once()
    mock_runner.logger.warning.assert_any_call("✖ test stream (code 124)")


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


@patch("routine_workflow.utils.cmd_exists", return_value=True)
@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel(mock_gather: Mock, mock_cmd: Mock, mock_exists: Mock, mock_runner: Mock):
    """Test parallel autoimport."""
    mock_py_files = [Path("test.py")]
    mock_gather.return_value = mock_py_files
    mock_cmd.return_value = {"success": True, "stdout": "", "stderr": ""}
    mock_runner.config.dry_run = False

    run_autoimport_parallel(mock_runner)

    mock_gather.assert_called_once_with(mock_runner.config)
    mock_runner.logger.info.assert_any_call("Autoimport complete: 1/1 successful")


@patch("routine_workflow.utils.cmd_exists", return_value=True)
@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel_no_files(mock_gather: Mock, mock_cmd: Mock, mock_exists: Mock, mock_runner: Mock):
    """Test skip on no files."""
    mock_gather.return_value = []
    mock_runner.config.dry_run = False

    run_autoimport_parallel(mock_runner)

    mock_runner.logger.info.assert_called_with("No files to process")


@patch("routine_workflow.utils.cmd_exists", return_value=True)
@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel_dry_run(mock_gather: Mock, mock_cmd: Mock, mock_exists: Mock, mock_runner: Mock):
    """Test dry-run skip."""
    mock_py_files = [Path("test.py")]
    mock_gather.return_value = mock_py_files
    mock_runner.config.dry_run = True

    run_autoimport_parallel(mock_runner)

    mock_runner.logger.info.assert_called_with("DRY-RUN: Would process 1 files")


@patch("routine_workflow.utils.cmd_exists", return_value=True)
@patch("routine_workflow.utils.as_completed")
@patch("routine_workflow.utils.ThreadPoolExecutor")
@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel_worker_exception(
    mock_gather, mock_cmd, mock_executor, mock_as_completed, mock_exists, mock_runner: Mock
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


@patch("routine_workflow.utils.cmd_exists", return_value=True)
@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_parallel_completion(mock_gather: Mock, mock_cmd: Mock, mock_exists: Mock, mock_runner: Mock):
    """Test completion logger in success case."""
    mock_py_files = [Path("test.py")]
    mock_gather.return_value = mock_py_files
    mock_cmd.return_value = {"success": True, "stdout": "", "stderr": ""}
    mock_runner.config.dry_run = False

    run_autoimport_parallel(mock_runner)

    mock_runner.logger.info.assert_called_with("Autoimport complete: 1/1 successful")