"""Tests for step4: Backup project."""

from unittest.mock import patch, Mock
from datetime import datetime
import pytest
from pathlib import Path

from routine_workflow.steps.step4 import backup_project
from routine_workflow.runner import WorkflowRunner
from routine_workflow.utils import run_command, cmd_exists


def test_backup_missing_script(mock_runner: Mock):
    """Test skips if script missing."""
    mock_runner.config.backup_script = Mock()
    mock_runner.config.backup_script.exists.return_value = False

    result = backup_project(mock_runner)

    assert result is True
    mock_runner.logger.info.assert_called_with('Script missing - skip')


@patch('routine_workflow.steps.step4.cmd_exists')
def test_backup_no_python3(mock_cmd_exists, mock_runner: Mock):
    """Test skips if no python3."""
    mock_runner.config.backup_script = Mock()
    mock_runner.config.backup_script.exists.return_value = True
    mock_cmd_exists.return_value = False

    result = backup_project(mock_runner)

    assert result is True
    mock_runner.logger.warning.assert_called_with('python3 not found - skipping backup')


@patch('routine_workflow.steps.step4.run_command')
@patch('datetime.datetime')
def test_backup_dry_run(mock_datetime, mock_run, mock_runner: Mock):
    """Test dry-run uses --dry-run flag."""
    mock_datetime.now.return_value.strftime.return_value = '20251031_180000_routine'
    mock_runner.config.backup_script = Mock()
    mock_runner.config.backup_script.exists.return_value = True
    mock_runner.config.dry_run = True
    mock_runner.config.auto_yes = False
    mock_runner.config.project_root = Path('/tmp/project')
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    result = backup_project(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Backup project', ['python3', str(mock_runner.config.backup_script), '20251031_180000_routine', '--archive', '--dry-run'],
        cwd=mock_runner.config.project_root, timeout=900.0, fatal=False
    )
    assert result is True


@patch('routine_workflow.steps.step4.run_command')
@patch('datetime.datetime')
def test_backup_auto_yes(mock_datetime, mock_run, mock_runner: Mock):
    """Test auto-yes uses --yes flag."""
    mock_datetime.now.return_value.strftime.return_value = '20251031_180000_routine'
    mock_runner.config.backup_script = Mock()
    mock_runner.config.backup_script.exists.return_value = True
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    mock_runner.config.project_root = Path('/tmp/project')
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    result = backup_project(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Backup project', ['python3', str(mock_runner.config.backup_script), '20251031_180000_routine', '--archive', '--yes', '--yes'],
        cwd=mock_runner.config.project_root, timeout=900.0, fatal=False
    )
    assert result is True


@patch('routine_workflow.steps.step4.run_command')
@patch('datetime.datetime')
def test_backup_success_noninteractive(mock_datetime, mock_run, mock_runner: Mock):
    """Test success handling."""
    mock_datetime.now.return_value.strftime.return_value = '20251031_180000_routine'
    mock_runner.config.backup_script = Mock()
    mock_runner.config.backup_script.exists.return_value = True
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    mock_runner.config.project_root = Path('/tmp/project')
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    result = backup_project(mock_runner)

    assert result is True
    mock_runner.logger.info.assert_called_with('Backup completed successfully')


@patch('routine_workflow.steps.step4.run_command')
@patch('datetime.datetime')
def test_backup_failure_no_fail_on(mock_datetime, mock_run, mock_runner: Mock):
    """Test failure without fail_on_backup continues."""
    mock_datetime.now.return_value.strftime.return_value = '20251031_180000_routine'
    mock_runner.config.backup_script = Mock()
    mock_runner.config.backup_script.exists.return_value = True
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    mock_runner.config.fail_on_backup = False
    mock_runner.config.project_root = Path('/tmp/project')
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": False, "stdout": "", "stderr": "Failed"}

    result = backup_project(mock_runner)

    assert result is True
    mock_runner.logger.warning.assert_called_with('Backup failed or skipped')


@patch('routine_workflow.steps.step4.run_command')
@patch('datetime.datetime')
def test_backup_fail_abort(mock_datetime, mock_run, mock_runner: Mock):
    """Test abort on fail with flag."""
    mock_datetime.now.return_value.strftime.return_value = '20251031_180000_routine'
    mock_runner.config.backup_script = Mock()
    mock_runner.config.backup_script.exists.return_value = True
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    mock_runner.config.fail_on_backup = True
    mock_runner.config.project_root = Path('/tmp/project')
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": False, "stdout": "", "stderr": "Failed"}

    result = backup_project(mock_runner)

    assert result is False
    mock_runner.logger.error.assert_called_with('Backup failed + fail_on_backup - abort')