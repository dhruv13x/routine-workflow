"""Tests for step3: Clean caches."""

from unittest.mock import patch, Mock
import pytest
from pathlib import Path

from routine_workflow.steps.step3 import clean_caches
from routine_workflow.runner import WorkflowRunner
from routine_workflow.utils import run_command, cmd_exists


def test_clean_caches_missing(mock_runner: Mock):
    """Test skips if missing."""
    mock_runner.config.clean_script = Mock()
    mock_runner.config.clean_script.exists.return_value = False

    clean_caches(mock_runner)

    mock_runner.logger.info.assert_called_with('Script missing - skip')


@patch('routine_workflow.steps.step3.cmd_exists')
def test_clean_caches_no_python3(mock_cmd_exists, mock_runner: Mock):
    """Test skips if no python3."""
    mock_runner.config.clean_script = Mock()
    mock_runner.config.clean_script.exists.return_value = True
    mock_cmd_exists.return_value = False

    clean_caches(mock_runner)

    assert mock_runner.logger.warning.called
    mock_runner.logger.warning.assert_called_with('python3 not found - skipping cleanup')


@patch('routine_workflow.steps.step3.run_command')
def test_clean_caches_exists(mock_run, mock_runner: Mock):
    """Test runs script if exists."""
    mock_script = Mock()
    mock_script.exists.return_value = True
    mock_runner.config.clean_script = mock_script
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = False
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    clean_caches(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Clean caches', ['python3', str(mock_runner.config.clean_script), str(mock_runner.config.project_root), '--allow-root', '--yes'],
        cwd=mock_runner.config.project_root, timeout=300.0, fatal=False
    )
    mock_runner.logger.info.assert_called_with('Cache cleanup completed successfully')


@patch('routine_workflow.steps.step3.run_command')
def test_clean_caches_dry_run(mock_run, mock_runner: Mock):
    """Test dry-run uses --preview flag."""
    mock_script = Mock()
    mock_script.exists.return_value = True
    mock_runner.config.clean_script = mock_script
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.dry_run = True
    mock_runner.config.auto_yes = False
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    clean_caches(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Clean caches', ['python3', str(mock_runner.config.clean_script), str(mock_runner.config.project_root), '--allow-root', '--preview'],
        cwd=mock_runner.config.project_root, timeout=300.0, fatal=False
    )
    mock_runner.logger.info.assert_called_with('Cache cleanup completed successfully')


@patch('routine_workflow.steps.step3.run_command')
def test_clean_caches_auto_yes(mock_run, mock_runner: Mock):
    """Test auto-yes uses --yes flag."""
    mock_script = Mock()
    mock_script.exists.return_value = True
    mock_runner.config.clean_script = mock_script
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    clean_caches(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Clean caches', ['python3', str(mock_runner.config.clean_script), str(mock_runner.config.project_root), '--allow-root', '--yes', '--yes'],
        cwd=mock_runner.config.project_root, timeout=300.0, fatal=False
    )


@patch('routine_workflow.steps.step3.run_command')
def test_clean_caches_failure(mock_run, mock_runner: Mock):
    """Test failure handling."""
    mock_script = Mock()
    mock_script.exists.return_value = True
    mock_runner.config.clean_script = mock_script
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": False, "stdout": "", "stderr": "Failed"}

    clean_caches(mock_runner)

    mock_runner.logger.warning.assert_called_with('Cache cleanup failed or skipped')