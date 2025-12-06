
import pytest
import sys
import logging
import subprocess
import threading
import shutil
import os
import signal
from unittest.mock import patch, Mock, MagicMock, ANY
from pathlib import Path
from logging import StreamHandler, Formatter
from logging.handlers import RotatingFileHandler

from routine_workflow.utils import (
    setup_logging, run_command, cmd_exists, should_exclude,
    gather_py_files, run_autoimport_parallel, setup_signal_handlers,
    JSONFormatter, _has_rich
)
from routine_workflow.config import WorkflowConfig
from routine_workflow.runner import WorkflowRunner
from routine_workflow.errors import CommandNotFoundError


@pytest.fixture(autouse=True)
def clear_logger():
    """Clear logger handlers before each test to avoid persistence issues."""
    logger = logging.getLogger("routine_workflow")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    logger.handlers.clear()
    yield


@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Create a temporary project root with a log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return tmp_path

@pytest.fixture
def mock_config(tmp_path: Path) -> WorkflowConfig:
    """Fixture for a mock WorkflowConfig."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return WorkflowConfig(
        project_root=tmp_path,
        log_dir=log_dir,
        log_file=log_dir / "workflow.log",
        lock_dir=tmp_path / "workflow.lock",
        dry_run=False,
    )

@pytest.fixture
def mock_runner(mock_config: WorkflowConfig) -> WorkflowRunner:
    """Fixture for a mock WorkflowRunner."""
    runner = WorkflowRunner(mock_config)
    runner.logger = MagicMock(spec=logging.Logger)
    return runner


# --- JSONFormatter Tests ---
def test_json_formatter_basic():
    formatter = JSONFormatter()
    record = logging.LogRecord("name", logging.INFO, "pathname", 10, "message", (), None)
    formatted = formatter.format(record)
    import json
    data = json.loads(formatted)
    assert data["message"] == "message"
    assert data["level"] == "INFO"

def test_json_formatter_with_extra():
    formatter = JSONFormatter()
    record = logging.LogRecord("name", logging.INFO, "pathname", 10, "message", (), None)
    record.custom_attr = "custom_value"
    formatted = formatter.format(record)
    import json
    data = json.loads(formatted)
    assert data["custom_attr"] == "custom_value"

def test_json_formatter_with_exception():
    formatter = JSONFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        exc_info = sys.exc_info()
    
    record = logging.LogRecord("name", logging.ERROR, "pathname", 10, "error message", (), exc_info)
    formatted = formatter.format(record)
    import json
    data = json.loads(formatted)
    assert "exception" in data
    assert "ValueError: test error" in data["exception"]


# --- setup_logging Tests ---
def test_setup_logging_json_format(temp_project_root: Path):
    log_dir = temp_project_root / "logs"
    log_file = log_dir / "routine_test.log"
    config = WorkflowConfig(
        project_root=temp_project_root,
        log_dir=log_dir,
        log_file=log_file,
        lock_dir=temp_project_root / "lock",
        log_format="json"
    )
    
    with patch('routine_workflow.utils._has_rich', return_value=False):
        logger = setup_logging(config)

    fh = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))
    assert isinstance(fh.formatter, JSONFormatter)


def test_setup_logging_existing_handlers(mock_config: WorkflowConfig):
    logger = logging.getLogger("routine_workflow")
    logger.addHandler(logging.NullHandler())

    setup_logging(mock_config)

    # Should warn and return existing logger without adding new handlers
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.NullHandler)

def test_setup_logging_plain(mock_config: WorkflowConfig):
    """Test setup_logging when rich is not available."""
    with patch('routine_workflow.utils._has_rich', return_value=False):
        logger = setup_logging(mock_config)

    assert len(logger.handlers) == 2
    # Verify StreamHandler
    sh = next(h for h in logger.handlers if isinstance(h, StreamHandler) and not isinstance(h, RotatingFileHandler))
    assert isinstance(sh, StreamHandler)


# --- run_command Tests ---
@patch("routine_workflow.utils.subprocess.Popen")
@patch('routine_workflow.utils._has_rich', return_value=False)
def test_run_command_stream_exception_in_thread(mock_has_rich, mock_popen, mock_runner: Mock):
    """Test exception handling in streaming thread."""
    mock_proc = MagicMock()
    mock_proc.wait.return_value = 0
    # Simulate readline raising exception
    mock_proc.stdout.readline.side_effect = Exception("Read error")
    mock_proc.stderr.readline.side_effect = [""]
    mock_popen.return_value = mock_proc

    result = run_command(mock_runner, "test stream", ["echo"], stream=True)

    assert result["success"] is True
    # Logger should have debug message about suppression
    mock_runner.logger.debug.assert_any_call("stream thread suppressed: Read error")

@patch("routine_workflow.utils.subprocess.run")
def test_run_command_file_not_found_no_fatal(mock_run, mock_runner):
    mock_run.side_effect = FileNotFoundError("Not found")

    result = run_command(mock_runner, "test", ["cmd"])

    assert result["success"] is False
    assert "FileNotFoundError" in result["stderr"]
    mock_runner.logger.error.assert_called_with("Command not found for: test")

@patch("routine_workflow.utils.subprocess.run")
def test_run_command_exception_no_fatal(mock_run, mock_runner):
    mock_run.side_effect = Exception("General failure")

    result = run_command(mock_runner, "test", ["cmd"])

    assert result["success"] is False
    assert "Exception: General failure" in result["stderr"]

@patch("routine_workflow.utils.subprocess.run")
@patch('routine_workflow.utils._has_rich', return_value=True)
def test_run_command_rich_logging(mock_has_rich, mock_run, mock_runner):
    mock_run.return_value = MagicMock(returncode=0, stdout="out line", stderr="err line")

    run_command(mock_runner, "test", ["cmd"])

    mock_runner.logger.info.assert_any_call("[green]  out line[/green]")
    mock_runner.logger.warning.assert_any_call("[red]  err line[/red]")

@patch("routine_workflow.utils.subprocess.Popen")
@patch('routine_workflow.utils._has_rich', return_value=True)
def test_run_command_stream_rich_logging(mock_has_rich, mock_popen, mock_runner):
    mock_proc = MagicMock()
    mock_proc.stdout.readline.side_effect = ["out line\n", ""]
    mock_proc.stderr.readline.side_effect = ["err line\n", ""]
    mock_proc.wait.return_value = 0
    mock_popen.return_value = mock_proc

    run_command(mock_runner, "test", ["cmd"], stream=True)

    # We rely on thread execution, which might be async.
    # But mock Popen objects are synchronous in their methods here.
    # The threads run readline loop.

    # Assertions might be flaky without joining threads, but since we mock wait/readline,
    # threads should exit quickly.
    import time
    time.sleep(0.1)

    mock_runner.logger.info.assert_any_call("[green]  out line[/green]")
    mock_runner.logger.warning.assert_any_call("[red]  err line[/red]")


@patch("routine_workflow.utils.subprocess.run")
def test_run_command_string_command_no_shell(mock_run, mock_runner):
    """Test that string command is shlex split if shell=False."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    run_command(mock_runner, "test", "ls -l", shell=False)

    mock_run.assert_called_with(
        ["ls", "-l"],
        cwd=ANY,
        capture_output=True,
        text=True,
        shell=False,
        input=None,
        timeout=300.0
    )

@patch("routine_workflow.utils.subprocess.run")
def test_run_command_list_command_shell(mock_run, mock_runner):
    """Test that list command is joined and quoted if shell=True."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    
    run_command(mock_runner, "test", ["ls", "-l", "file with space"], shell=True)

    # shlex.quote should wrap 'file with space'
    # 'ls' and '-l' remain same.
    # command should be "ls -l 'file with space'"

    args, kwargs = mock_run.call_args
    assert args[0] == "ls -l 'file with space'"
    assert kwargs['shell'] is True

@patch("routine_workflow.utils.subprocess.run")
def test_run_command_timeout_not_stream(mock_run, mock_runner):
    mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)
    result = run_command(mock_runner, "test", "cmd", timeout=10)
    assert result["success"] is False
    assert "TimeoutExpired" in result["stderr"]

# --- gather_py_files & should_exclude Tests ---
def test_should_exclude_relativize_fail(mock_config):
    # Path on different drive or unrelated path
    if sys.platform == "win32":
        p = Path("Z:/test.py")
    else:
        p = Path("/different/root/test.py")

    # Assuming project root is tmp path
    assert should_exclude(mock_config, p) is True

def test_gather_py_files_sorting(mock_config):
    # create files in random order
    (mock_config.project_root / "b.py").touch()
    (mock_config.project_root / "a.py").touch()

    files = gather_py_files(mock_config)
    assert files[0].name == "a.py"
    assert files[1].name == "b.py"


# --- run_autoimport_parallel Tests ---
@patch("routine_workflow.utils.cmd_exists", return_value=True)
@patch("routine_workflow.utils.run_command")
@patch("routine_workflow.utils.gather_py_files")
def test_run_autoimport_worker_exception_logging(mock_gather, mock_cmd, mock_exists, mock_runner):
    # We want to force an exception inside the thread pool execution
    mock_gather.return_value = [Path("test.py")]

    # run_command raises exception? No, run_command catches exceptions.
    # But run_autoimport_parallel has a try-except block around fut.result().
    # So if submit raises or result raises...

    # We can patch ThreadPoolExecutor to return a future that raises on result()
    with patch("routine_workflow.utils.ThreadPoolExecutor") as MockExecutor:
        mock_future = Mock()
        mock_future.result.side_effect = Exception("Worker died")

        mock_executor_instance = MockExecutor.return_value.__enter__.return_value
        mock_executor_instance.submit.return_value = mock_future

        # as_completed needs to yield this future
        with patch("routine_workflow.utils.as_completed", return_value=[mock_future]):
             run_autoimport_parallel(mock_runner)

    mock_runner.logger.warning.assert_called_with("autoimport worker exception: Worker died")

# --- setup_signal_handlers Tests ---
@patch("routine_workflow.utils.cleanup_and_exit")
@patch("signal.signal")
def test_signal_handler_execution(mock_signal, mock_cleanup, mock_runner):
    setup_signal_handlers(mock_runner)

    # Extract handler
    handler = mock_signal.call_args_list[0][0][1]

    # Call it
    handler(signal.SIGINT, None)

    mock_cleanup.assert_called_with(mock_runner, 130) # 128 + 2

@patch("routine_workflow.utils.cleanup_and_exit")
@patch("signal.signal")
def test_signal_handler_exception_fallback(mock_signal, mock_cleanup, mock_runner):
    setup_signal_handlers(mock_runner)
    handler = mock_signal.call_args_list[0][0][1]

    # Make cleanup raise generic exception
    mock_cleanup.side_effect = Exception("Cleanup failed")

    with patch("os._exit") as mock_os_exit:
        handler(signal.SIGINT, None)
        mock_os_exit.assert_called_with(1)

# --- _has_rich Tests ---
def test_has_rich_present():
    with patch("importlib.util.find_spec", return_value=True):
        assert _has_rich() is True

def test_has_rich_absent():
    with patch("importlib.util.find_spec", return_value=None):
        assert _has_rich() is False
