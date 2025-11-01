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
    mock_config.code_dump_run_cmd = ['code-dump', 'batch', 'run']
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

