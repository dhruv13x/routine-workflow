"""Tests for step1: Delete old dumps."""

from unittest.mock import Mock, patch
from pathlib import Path
import pytest

from routine_workflow.steps.step1 import delete_old_dumps
from routine_workflow.runner import WorkflowRunner
from routine_workflow.utils import cmd_exists, run_command


@pytest.fixture
def mock_runner() -> Mock:
    """Mock WorkflowRunner with minimal config."""
    runner = Mock(spec=WorkflowRunner)
    runner.logger = Mock()  # Essential for log access
    config = Mock(spec='WorkflowConfig')
    config.create_dump_clean_cmd = ['create-dump', 'batch', 'clean']
    config.project_root = Path('/tmp/project')
    runner.config = config
    return runner


def test_delete_old_dumps_header(mock_runner: Mock):
    """Test header logs always."""
    mock_runner.config.dry_run = False

    delete_old_dumps(mock_runner)

    mock_runner.logger.info.assert_any_call('=' * 60)
    mock_runner.logger.info.assert_any_call('STEP 1: Delete old code dumps (via create-dump tool)')


@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_no_tool(mock_exists, mock_runner: Mock):
    """Test skip if create-dump not found."""
    mock_runner.config.dry_run = False
    mock_exists.return_value = False

    delete_old_dumps(mock_runner)

    mock_runner.logger.warning.assert_called_once_with('create-dump not found - skipping cleanup')


@patch('routine_workflow.steps.step1.run_command')
@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_dry_run(mock_exists, mock_run, mock_runner: Mock):
    """Test dry-run invokes tool with -d for native preview."""
    mock_runner.config.dry_run = True
    mock_runner.config.auto_yes = False
    mock_exists.return_value = True
    mock_run.return_value = {'success': True}

    delete_old_dumps(mock_runner)

    expected_cmd = ['create-dump', 'batch', 'clean', '-d']
    mock_run.assert_called_once_with(
        mock_runner, 'Clean old code dumps', expected_cmd,
        cwd=mock_runner.config.project_root, timeout=300.0, fatal=False
    )
    mock_runner.logger.info.assert_any_call('Code-dump cleanup completed successfully')


@patch('routine_workflow.steps.step1.run_command')
@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_real_run(mock_exists, mock_run, mock_runner: Mock):
    """Test real-run invokes with -nd, -y."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True  # Ignored; -y forced
    mock_exists.return_value = True
    mock_run.return_value = {'success': True}

    delete_old_dumps(mock_runner)

    expected_cmd = ['create-dump', 'batch', 'clean', '-nd', '-y']
    mock_run.assert_called_once_with(
        mock_runner, 'Clean old code dumps', expected_cmd,
        cwd=mock_runner.config.project_root, timeout=300.0, fatal=False
    )
    mock_runner.logger.info.assert_called_with('Code-dump cleanup completed successfully')


@patch('routine_workflow.steps.step1.run_command')
@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_failure(mock_exists, mock_run, mock_runner: Mock):
    """Test handles tool failure gracefully."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = False  # Ignored; -y forced
    mock_exists.return_value = True
    mock_run.return_value = {'success': False}

    delete_old_dumps(mock_runner)

    expected_cmd = ['create-dump', 'batch', 'clean', '-nd', '-y']
    mock_run.assert_called_once_with(
        mock_runner, 'Clean old code dumps', expected_cmd,
        cwd=mock_runner.config.project_root, timeout=300.0, fatal=False
    )
    mock_runner.logger.warning.assert_called_with('Code-dump cleanup failed or skipped')


@patch('routine_workflow.steps.step1.run_command')
@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_auto_yes(mock_exists, mock_run, mock_runner: Mock):
    """Test cmd building with -y flag (forced on -nd)."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    mock_exists.return_value = True

    delete_old_dumps(mock_runner)

    call_args = mock_run.call_args[0][2]
    assert '-y' in call_args
    assert '-nd' in call_args