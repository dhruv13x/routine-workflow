# tests/test_steps/test_step3.py

"""Tests for step3: Clean caches."""

from unittest.mock import patch, Mock
import pytest
from pathlib import Path

from routine_workflow.steps.step3 import clean_caches
from routine_workflow.runner import WorkflowRunner
from routine_workflow.utils import run_command, cmd_exists


def test_clean_caches_missing(mock_runner: Mock):
    """Test skips if missing (now checks for pypurge command)."""
    # No-op placeholder or remove if not needed, but keeping for now as 'missing tool' check
    # logic is covered by 'no_pypurge' test below.
    pass


@patch('routine_workflow.steps.step3.cmd_exists')
def test_clean_caches_no_pypurge(mock_cmd_exists, mock_runner: Mock):
    """Test skips if no pypurge."""
    mock_cmd_exists.return_value = False

    clean_caches(mock_runner)

    assert mock_runner.logger.warning.called
    mock_runner.logger.warning.assert_called_with('pypurge not found - skipping cleanup')


@patch('routine_workflow.steps.step3.run_command')
def test_clean_caches_exists(mock_run, mock_runner: Mock):
    """Test runs pypurge if exists."""
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = False
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    clean_caches(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Clean caches', ['pypurge', str(mock_runner.config.project_root), '--allow-root', '-y'],
        cwd=mock_runner.config.project_root, timeout=300.0, fatal=False
    )
    mock_runner.logger.info.assert_called_with('Cache cleanup completed successfully')


@patch('routine_workflow.steps.step3.run_command')
def test_clean_caches_dry_run(mock_run, mock_runner: Mock):
    """Test dry-run uses -p flag."""
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.dry_run = True
    mock_runner.config.auto_yes = False
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    clean_caches(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Clean caches', ['pypurge', str(mock_runner.config.project_root), '--allow-root', '-p'],
        cwd=mock_runner.config.project_root, timeout=300.0, fatal=False
    )
    mock_runner.logger.info.assert_called_with('Cache cleanup completed successfully')


@patch('routine_workflow.steps.step3.run_command')
def test_clean_caches_auto_yes(mock_run, mock_runner: Mock):
    """Test auto-yes ensures -y flag."""
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    clean_caches(mock_runner)

    # 'auto_yes' logic adds '-y' even if '-y' was already there? 
    # In step3.py: if not dry_run: cmd.append('-y'). Then if auto_yes and '-y' not in cmd: append.
    # So we expect just one '-y' unless logic is flawed.
    # Checking step3.py logic: 
    # if dry_run: -p else: -y. 
    # if auto_yes and '-y' not in cmd: append.
    # So if dry_run=False, we get '-y'. Then auto_yes check sees '-y' and skips.
    # Wait, test output showed `['-y']` in actual call in previous failure.
    # Let's match exact expectation.
    
    mock_run.assert_called_once_with(
        mock_runner, 'Clean caches', ['pypurge', str(mock_runner.config.project_root), '--allow-root', '-y'],
        cwd=mock_runner.config.project_root, timeout=300.0, fatal=False
    )


@patch('routine_workflow.steps.step3.run_command')
def test_clean_caches_failure(mock_run, mock_runner: Mock):
    """Test failure handling."""
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    # --- FIXED: Return a dict, not a bool ---
    mock_run.return_value = {"success": False, "stdout": "", "stderr": "Failed"}

    clean_caches(mock_runner)

    mock_runner.logger.warning.assert_called_with('Cache cleanup failed or skipped')
