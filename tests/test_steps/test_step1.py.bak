"""Tests for step1: Delete old dumps."""

from unittest.mock import Mock, patch
from pathlib import Path
import pytest

from routine_workflow.steps.step1 import delete_old_dumps
from routine_workflow.runner import WorkflowRunner
from routine_workflow.utils import cmd_exists, run_command


def test_delete_old_dumps_header(mock_runner: Mock):
    """Test header logs always."""
    mock_runner.config.dry_run = False

    delete_old_dumps(mock_runner)

    mock_runner.logger.info.assert_any_call('=' * 60)
    mock_runner.logger.info.assert_any_call('STEP 1: Delete old code dumps (via code-dump tool)')


@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_no_tool(mock_exists, mock_runner: Mock):
    """Test skip if code-dump not found."""
    mock_runner.config.dry_run = False
    mock_exists.return_value = False

    delete_old_dumps(mock_runner)

    mock_runner.logger.warning.assert_called_once_with('code-dump not found - skipping cleanup')


@patch('routine_workflow.steps.step1.run_command')
@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_dry_run(mock_exists, mock_run, mock_runner: Mock):
    """Test dry-run invokes tool with -d for native preview."""
    mock_runner.config.dry_run = True
    mock_runner.config.auto_yes = False
    mock_runner.config.project_root = Path('/tmp/project')
    mock_exists.return_value = True
    mock_run.return_value = True  # Tool succeeds with dry flag

    delete_old_dumps(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Clean old code dumps', ['code-dump', 'batch', 'clean', '/tmp/project', '-d'],
        cwd=mock_runner.config.project_root, timeout=60.0, fatal=False
    )
    mock_runner.logger.info.assert_any_call('Code-dump cleanup completed successfully')  # Post-tool success


@patch('routine_workflow.steps.step1.run_command')
@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_real_run(mock_exists, mock_run, mock_runner: Mock):
    """Test real-run invokes with -nd."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    mock_runner.config.project_root = Path('/tmp/project')
    mock_exists.return_value = True
    mock_run.return_value = True

    delete_old_dumps(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Clean old code dumps', ['code-dump', 'batch', 'clean', '/tmp/project', '-nd', '-y'],
        cwd=mock_runner.config.project_root, timeout=60.0, fatal=False
    )
    mock_runner.logger.info.assert_called_with('Code-dump cleanup completed successfully')


@patch('routine_workflow.steps.step1.run_command')
@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_failure(mock_exists, mock_run, mock_runner: Mock):
    """Test handles tool failure gracefully."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = False
    mock_runner.config.project_root = Path('/tmp/project')
    mock_exists.return_value = True
    mock_run.return_value = False

    delete_old_dumps(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Clean old code dumps', ['code-dump', 'batch', 'clean', '/tmp/project', '-nd'],
        cwd=mock_runner.config.project_root, timeout=60.0, fatal=False
    )
    mock_runner.logger.warning.assert_called_with('Code-dump cleanup failed or skipped')


@patch('routine_workflow.steps.step1.run_command')
@patch('routine_workflow.steps.step1.cmd_exists')
def test_delete_old_dumps_auto_yes(mock_exists, mock_run, mock_runner: Mock):
    """Test cmd building with -y flag."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    mock_runner.config.project_root = Path('/tmp/project')
    mock_exists.return_value = True

    delete_old_dumps(mock_runner)

    call_args = mock_run.call_args[0][2]
    assert '-y' in call_args
    assert str(mock_runner.config.project_root) in call_args