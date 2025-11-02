import pytest
import logging
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

from routine_workflow.runner import WorkflowRunner
from routine_workflow.config import WorkflowConfig
from routine_workflow.steps import (
    delete_old_dumps,
    reformat_code,
    clean_caches,
    backup_project,
    generate_dumps,
)  # Import for patching



"""Tests for runner orchestration."""

import signal
from unittest.mock import patch, Mock, ANY
import pytest
from pathlib import Path

from routine_workflow.runner import WorkflowRunner
from routine_workflow.config import WorkflowConfig


@patch("routine_workflow.runner.setup_logging")
@patch("routine_workflow.runner.setup_signal_handlers")
def test_init(mock_handlers: Mock, mock_logging: Mock, mock_config: WorkflowConfig):
    """Test runner init sets up logging/signals."""
    runner = WorkflowRunner(mock_config)

    mock_logging.assert_called_once_with(mock_config)
    mock_handlers.assert_called_once_with(runner)
    assert runner.config == mock_config
    assert runner._lock_acquired is False
    assert runner._pid_path is None


@patch('routine_workflow.runner.delete_old_dumps')
@patch('routine_workflow.runner.reformat_code')
@patch('routine_workflow.runner.clean_caches')
@patch('routine_workflow.runner.backup_project')
@patch('routine_workflow.runner.generate_dumps')
@patch('routine_workflow.runner.lock_context')
def test_run_success(mock_lock, mock_generate, mock_backup, mock_clean, mock_reformat, mock_delete, mock_config: WorkflowConfig):
    """Test successful run calls all steps."""
    mock_backup.return_value = True
    mock_lock.__enter__.return_value = None

    runner = WorkflowRunner(mock_config)
    with patch.object(runner, 'logger') as mock_log:
        result = runner.run()

    assert result == 0
    mock_delete.assert_called_once_with(runner)
    mock_reformat.assert_called_once_with(runner)
    mock_clean.assert_called_once_with(runner)
    mock_backup.assert_called_once_with(runner)
    mock_generate.assert_called_once_with(runner)
    mock_log.info.assert_any_call('WORKFLOW SUCCESS')


def test_run_backup_fail(mock_config: Mock):
    """Test abort on backup fail."""
    mock_config.backup_script = Mock()
    mock_config.backup_script.exists.return_value = True  # Force "exists"
    mock_config.fail_on_backup = True

    runner = WorkflowRunner(mock_config)
    with patch('routine_workflow.runner.lock_context'), \
         patch('routine_workflow.runner.delete_old_dumps'), \
         patch('routine_workflow.runner.reformat_code'), \
         patch('routine_workflow.runner.clean_caches'), \
         patch('routine_workflow.runner.backup_project') as mock_backup, \
         patch('routine_workflow.runner.generate_dumps'), \
         patch.object(runner, 'logger'):

        mock_backup.return_value = False
        result = runner.run()

    assert result == 2
    mock_backup.assert_called_once_with(runner)


@patch('routine_workflow.runner.lock_context')
def test_run_exception(mock_lock, mock_config: WorkflowConfig):
    """Test exception handling returns 1."""
    mock_lock.__enter__.return_value = None  # Enter succeeds
    runner = WorkflowRunner(mock_config)
    with patch('routine_workflow.runner.delete_old_dumps') as mock_delete, \
         patch.object(runner, 'logger') as mock_log:
        mock_delete.side_effect = Exception('Test error')
        result = runner.run()

    assert result == 1
    mock_log.exception.assert_called_once()


@patch('routine_workflow.runner.setup_signal_handlers')  # Skip SIGINT/SIGTERM
@patch('routine_workflow.runner.signal.alarm')
@patch('routine_workflow.runner.signal.signal')
@patch('routine_workflow.runner.delete_old_dumps')
@patch('routine_workflow.runner.reformat_code')
@patch('routine_workflow.runner.clean_caches')
@patch('routine_workflow.runner.backup_project')
@patch('routine_workflow.runner.generate_dumps')
@patch('routine_workflow.runner.lock_context')
def test_workflow_timeout_alarm(
    mock_lock, mock_generate, mock_backup, mock_clean, mock_reformat, mock_delete,
    mock_signal, mock_alarm, mock_handlers, mock_config: WorkflowConfig
):
    """Test SIGALRM setup and teardown."""
    # Mock config attrs to prevent step failures
    mock_config.create_dump_run_cmd = ['create-dump', 'batch', 'run']
    mock_config.backup_script = Mock(exists=False)  # Skip backup
    mock_config.clean_script = Mock(exists=False)  # Skip clean
    runner = WorkflowRunner(mock_config)
    runner.config.workflow_timeout = 300

    mock_backup.return_value = True
    mock_lock.__enter__.return_value = None

    result = runner.run()

    mock_signal.assert_any_call(signal.SIGALRM, ANY)  # SIGALRM call
    assert mock_alarm.call_count == 2
    mock_alarm.assert_any_call(300)
    mock_alarm.assert_any_call(0)
    assert result == 0  # Success with mocked steps


@patch('routine_workflow.runner.setup_signal_handlers')  # Skip SIGINT/SIGTERM
@patch('routine_workflow.runner.delete_old_dumps')
@patch('routine_workflow.runner.reformat_code')
@patch('routine_workflow.runner.clean_caches')
@patch('routine_workflow.runner.backup_project')
@patch('routine_workflow.runner.generate_dumps')
@patch('routine_workflow.runner.lock_context')
@patch('routine_workflow.runner.signal.alarm')
@patch('routine_workflow.runner.signal.signal')
def test_run_no_timeout(
    mock_signal, mock_alarm, mock_lock, mock_generate, mock_backup, mock_clean, mock_reformat, mock_delete, mock_handlers, mock_config: WorkflowConfig
):
    """Test no alarm setup if timeout=0."""
    mock_lock.__enter__.return_value = None
    mock_config.workflow_timeout = 0
    runner = WorkflowRunner(mock_config)

    result = runner.run()

    mock_alarm.assert_not_called()
    mock_signal.assert_not_called()
    assert result == 0  # Success path


@patch('routine_workflow.runner.setup_signal_handlers')  # Skip SIGINT/SIGTERM
@patch('routine_workflow.runner.delete_old_dumps')
@patch('routine_workflow.runner.reformat_code')
@patch('routine_workflow.runner.clean_caches')
@patch('routine_workflow.runner.backup_project')
@patch('routine_workflow.runner.generate_dumps')
@patch('routine_workflow.runner.lock_context')
@patch('routine_workflow.runner.signal.alarm')
@patch('routine_workflow.runner.signal.signal')
def test_run_alarm_setup_exception(
    mock_signal, mock_alarm, mock_lock, mock_generate, mock_backup, mock_clean, mock_reformat, mock_delete, mock_handlers, mock_config: WorkflowConfig
):
    """Test alarm setup warning on exception."""
    mock_lock.__enter__.return_value = None
    mock_config.workflow_timeout = 300
    runner = WorkflowRunner(mock_config)
    with patch.object(runner, 'logger') as mock_log:
        mock_alarm.side_effect = Exception('Alarm error')
        result = runner.run()

    mock_log.warning.assert_called_with('Could not set workflow timeout alarm: Alarm error')
    assert result == 0  # Success despite alarm fail


@patch('routine_workflow.runner.setup_signal_handlers')  # Skip SIGINT/SIGTERM
@patch('routine_workflow.runner.delete_old_dumps')
@patch('routine_workflow.runner.reformat_code')
@patch('routine_workflow.runner.clean_caches')
@patch('routine_workflow.runner.backup_project')
@patch('routine_workflow.runner.generate_dumps')
@patch('routine_workflow.runner.lock_context')
@patch('routine_workflow.runner.signal.alarm')
@patch('routine_workflow.runner.signal.signal')
def test_run_alarm_teardown_exception(
    mock_signal, mock_alarm, mock_lock, mock_generate, mock_backup, mock_clean, mock_reformat, mock_delete, mock_handlers, mock_config: WorkflowConfig
):
    """Test alarm teardown exception ignored."""
    mock_lock.__enter__.return_value = None
    mock_config.workflow_timeout = 300
    runner = WorkflowRunner(mock_config)
    with patch.object(runner, 'logger') as mock_log:
        mock_alarm.side_effect = [None, Exception('Teardown error')]  # Setup ok, teardown fails
        result = runner.run()

    assert mock_alarm.call_count == 2
    mock_log.warning.assert_not_called()  # Exception in finally suppressed
    assert result == 0


@patch('routine_workflow.runner.setup_signal_handlers')  # Skip SIGINT/SIGTERM
@patch('routine_workflow.runner.delete_old_dumps')
@patch('routine_workflow.runner.reformat_code')
@patch('routine_workflow.runner.clean_caches')
@patch('routine_workflow.runner.backup_project')
@patch('routine_workflow.runner.generate_dumps')
@patch('routine_workflow.runner.lock_context')
def test_run_chdir(
    mock_lock, mock_generate, mock_backup, mock_clean, mock_reformat, mock_delete, mock_handlers, mock_config: WorkflowConfig
):
    """Test chdir to project_root."""
    mock_lock.__enter__.return_value = None
    mock_config.project_root = Path('/test/root')
    runner = WorkflowRunner(mock_config)
    with patch('os.chdir') as mock_chdir:
        result = runner.run()

    mock_chdir.assert_called_once_with(mock_config.project_root)
    assert result == 0





@pytest.fixture
def minimal_config(tmp_path: Path):
    """Minimal config for isolated tests."""
    return WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "routine_test.log",  # Valid Path to avoid None error
        lock_dir=tmp_path / "lock",
        clean_script=tmp_path / "clean.py",
        backup_script=tmp_path / "backup.py",
        create_dump_script=tmp_path / "dump.sh",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=1,
        workflow_timeout=0,
        exclude_patterns=[],
    )


@patch("routine_workflow.runner.signal.alarm")
@patch("routine_workflow.runner.generate_dumps")
@patch("routine_workflow.runner.delete_old_dumps")
@patch("routine_workflow.runner.clean_caches")
@patch("routine_workflow.runner.reformat_code")
@patch("routine_workflow.runner.backup_project")
@patch("routine_workflow.runner.lock_context")
def test_run_specific_steps(
    mock_lock,
    mock_backup,
    mock_reformat,
    mock_clean,
    mock_delete,
    mock_generate,
    mock_alarm,
    minimal_config: WorkflowConfig,
    caplog: pytest.LogCaptureFixture,
):
    """Test selective steps: filter, warn skips, invoke only targeted funcs."""
    # Setup mocks: steps return success; lock enters/exits cleanly
    mock_lock.return_value.__enter__.return_value = None  # No-op lock
    mock_delete.return_value = None
    mock_reformat.return_value = None
    mock_clean.return_value = None
    mock_backup.return_value = True  # Success for gating
    mock_generate.return_value = None
    mock_alarm.return_value = None  # No-op timeout

    # Enable caplog for INFO/WARNING
    caplog.set_level(logging.INFO)

    # Real runner with partial steps; enable propagation for caplog
    runner = WorkflowRunner(minimal_config, steps=["step2", "step4"])
    runner.logger.propagate = True  # Route named logger to root for capture
    result = runner.run()

    # Debug: Print captured count (remove post-validation)
    print(f"Caplog records captured: {len(caplog.records)}")

    # Assertions: filtering, warnings, invocations, outcome
    assert result == 0

    # Verify warning for skips (via caplog records; order-independent)
    skip_warnings = [rec for rec in caplog.records if "Skipping steps:" in rec.message]
    assert len(skip_warnings) == 1
    expected_steps = {"step1", "step3", "step5"}
    actual_steps = set(skip_warnings[0].message.split(": ")[1].strip().split(", "))
    assert actual_steps == expected_steps

    # Verify success log
    success_logs = [rec for rec in caplog.records if "WORKFLOW SUCCESS" in rec.message]
    assert len(success_logs) == 1

    # Only targeted steps called (others not)
    mock_reformat.assert_called_once_with(runner)  # step2
    mock_backup.assert_called_once_with(runner)    # step4
    mock_delete.assert_not_called()
    mock_clean.assert_not_called()
    mock_generate.assert_not_called()

    # Lock acquired/released
    mock_lock.assert_called_once()
    mock_lock.return_value.__exit__.assert_called_once_with(None, None, None)