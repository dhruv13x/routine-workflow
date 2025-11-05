"""Tests for step6: Commit hygiene snapshot to git."""

from unittest.mock import Mock, patch, call
import pytest
from pathlib import Path
from datetime import datetime

from routine_workflow.steps.step6 import commit_hygiene
from routine_workflow.runner import WorkflowRunner
from routine_workflow.config import WorkflowConfig
from routine_workflow.utils import cmd_exists, run_command


@pytest.fixture
def mock_runner(tmp_path: Path):
    """Mock runner with config and logger."""
    runner = Mock(spec=WorkflowRunner)
    runner.logger = Mock()  # Explicit for dynamic attr
    
    # Define a minimal config and attach it to the mock runner
    # This avoids needing to build a full config for every test
    config = Mock(spec=WorkflowConfig)
    config.project_root = tmp_path
    config.log_dir = tmp_path / "logs"
    config.log_file = tmp_path / "test.log"
    config.lock_dir = tmp_path / "lock"
    # Add all other fields with sensible defaults
    config.clean_script = tmp_path / "clean.py"
    config.backup_script = tmp_path / "backup.py"
    config.create_dump_script = tmp_path / "dump.sh"
    config.lock_ttl = 3600
    config.create_dump_clean_cmd = []
    config.create_dump_run_cmd = []
    config.fail_on_backup = False
    config.auto_yes = False
    config.dry_run = False # Default to false
    config.max_workers = 4
    config.test_cov_threshold = 85
    config.git_push = False # Default to false
    config.enable_security = False
    config.enable_dep_audit = False
    config.workflow_timeout = 0
    config.exclude_patterns = []
    
    runner.config = config
    return runner


@patch('routine_workflow.steps.step6.run_command')
@patch('routine_workflow.steps.step6.cmd_exists')
def test_commit_hygiene_skip_dry_run(mock_cmd_exists, mock_run, mock_runner: Mock):
    """Test dry_run=True calls 'git status'."""
    mock_runner.config.dry_run = True
    mock_runner.config.git_push = True # Ensure push is "enabled"
    mock_cmd_exists.return_value = True
    mock_run.return_value = {'success': True, 'stdout': '', 'stderr': ''}

    result = commit_hygiene(mock_runner)

    assert result is True
    mock_cmd_exists.assert_called_once_with('git')
    # Asserts the new dry-run behavior
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60),
        call('DRY-RUN: Checking git status (no commit/push).')
    ], any_order=False)
    # Check that 'git status' was called
    mock_run.assert_called_once_with(
        mock_runner,
        'Git status preview',
        ['git', 'status'],
        fatal=False,
        stream=True
    )


@patch('routine_workflow.steps.step6.run_command')
@patch('routine_workflow.steps.step6.cmd_exists')
def test_commit_hygiene_skip_disabled(mock_cmd_exists, mock_run, mock_runner: Mock):
    """Test skip if git_push=False (and dry_run=False)."""
    mock_runner.config.dry_run = False
    mock_runner.config.git_push = False
    mock_cmd_exists.return_value = True

    result = commit_hygiene(mock_runner)

    assert result is True
    mock_cmd_exists.assert_called_once_with('git')
    # Asserts the new "disabled" log message
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60),
        call('Git push is disabled via config, skipping step 6.')
    ], any_order=False)
    mock_run.assert_not_called() # No commands run


@patch('routine_workflow.steps.step6.run_command')
@patch('routine_workflow.steps.step6.cmd_exists')
def test_commit_hygiene_skip_missing_git(mock_cmd_exists, mock_run, mock_runner: Mock):
    """Test skip if git not found."""
    mock_runner.config.dry_run = False
    mock_runner.config.git_push = True
    mock_cmd_exists.return_value = False

    result = commit_hygiene(mock_runner)

    assert result is True
    mock_cmd_exists.assert_called_once_with('git')
    # Asserts the new "not found" log message
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60)
    ], any_order=False)
    mock_runner.logger.warning.assert_called_once_with('git command not found, skipping step 6.')
    mock_run.assert_not_called()


@patch('routine_workflow.steps.step6.run_command')
@patch('routine_workflow.steps.step6.datetime')
@patch('routine_workflow.steps.step6.cmd_exists')
def test_commit_hygiene_full_success_with_changes(mock_cmd_exists, mock_datetime, mock_run, mock_runner: Mock):
    """Test full success: add/commit/push all succeed (changes present)."""
    mock_runner.config.dry_run = False
    mock_runner.config.git_push = True
    mock_cmd_exists.return_value = True
    
    mock_datetime.now.return_value.strftime.return_value = '2025-11-03 12:00:00'
    commit_msg = 'routine_hygiene: 2025-11-03 12:00:00'
    
    # --- FIXED: Return dicts, not bools ---
    mock_run.side_effect = [
        {'success': True, 'stdout': '', 'stderr': ''},  # git add
        {'success': True, 'stdout': '', 'stderr': ''},  # git commit
        {'success': True, 'stdout': '', 'stderr': ''}   # git push
    ]

    result = commit_hygiene(mock_runner)

    assert result is True
    mock_datetime.now.assert_called_once()
    mock_run.assert_has_calls([
        call(mock_runner, 'git add', ['git', 'add', '.'], fatal=True),
        # --- FIXED: fatal=False for commit ---
        call(mock_runner, 'git commit', ['git', 'commit', '-m', commit_msg], fatal=False),
        call(mock_runner, 'git push', ['git', 'push', '-u', 'origin', 'main'], fatal=True)
    ])
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60),
        call(f'Hygiene snapshot committed & pushed: {commit_msg}')
    ], any_order=False)


@patch('routine_workflow.steps.step6.run_command')
@patch('routine_workflow.steps.step6.datetime')
@patch('routine_workflow.steps.step6.cmd_exists')
def test_commit_hygiene_success_no_changes(mock_cmd_exists, mock_datetime, mock_run, mock_runner: Mock):
    """Test success: add succeeds, commit fails (no changes), push is skipped."""
    mock_runner.config.dry_run = False
    mock_runner.config.git_push = True
    mock_cmd_exists.return_value = True

    mock_datetime.now.return_value.strftime.return_value = '2025-11-03 12:00:00'
    commit_msg = 'routine_hygiene: 2025-11-03 12:00:00'
    
    # --- FIXED: Return dicts, only 2 calls expected ---
    mock_run.side_effect = [
        {'success': True, 'stdout': '', 'stderr': ''},  # git add
        {'success': False, 'stdout': 'no changes', 'stderr': ''}  # git commit (fails)
    ]

    result = commit_hygiene(mock_runner)

    assert result is True
    mock_run.assert_has_calls([
        call(mock_runner, 'git add', ['git', 'add', '.'], fatal=True),
        # --- FIXED: fatal=False for commit ---
        call(mock_runner, 'git commit', ['git', 'commit', '-m', commit_msg], fatal=False)
    ])
    # --- FIXED: Assert git push was NOT called ---
    assert mock_run.call_count == 2
    
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60),
        call('No changes to commit; snapshot up-to-date')
    ], any_order=False)
    # Ensure "committed & pushed" was not logged
    assert not any('committed & pushed' in str(c) for c in mock_runner.logger.info.call_args_list)


@patch('routine_workflow.steps.step6.run_command')
@patch('routine_workflow.steps.step6.datetime')
@patch('routine_workflow.steps.step6.cmd_exists')
def test_commit_hygiene_add_failure(mock_cmd_exists, mock_datetime, mock_run, mock_runner: Mock):
    """Test early failure on git add."""
    mock_runner.config.dry_run = False
    mock_runner.config.git_push = True
    mock_cmd_exists.return_value = True
    
    # --- FIXED: Return dict ---
    mock_run.return_value = {'success': False, 'stdout': '', 'stderr': 'add failed'}

    result = commit_hygiene(mock_runner)

    assert result is False
    mock_run.assert_called_once_with(mock_runner, 'git add', ['git', 'add', '.'], fatal=True)
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60)
    ], any_order=False)
    # No commit/push calls, no success/no-changes logs
    assert not any('committed' in str(args) or 'up-to-date' in str(args) for args, _ in mock_runner.logger.info.call_args_list)


@patch('routine_workflow.steps.step6.run_command')
@patch('routine_workflow.steps.step6.datetime')
@patch('routine_workflow.steps.step6.cmd_exists')
def test_commit_hygiene_push_failure(mock_cmd_exists, mock_datetime, mock_run, mock_runner: Mock):
    """Test failure on push (after add/commit success)."""
    mock_runner.config.dry_run = False
    mock_runner.config.git_push = True
    mock_cmd_exists.return_value = True

    mock_datetime.now.return_value.strftime.return_value = '2025-11-03 12:00:00'
    commit_msg = 'routine_hygiene: 2025-11-03 12:00:00'
    
    # --- FIXED: Return dicts ---
    mock_run.side_effect = [
        {'success': True, 'stdout': '', 'stderr': ''},  # git add
        {'success': True, 'stdout': '', 'stderr': ''},  # git commit
        {'success': False, 'stdout': '', 'stderr': 'push failed'} # git push
    ]

    result = commit_hygiene(mock_runner)

    assert result is False
    mock_run.assert_has_calls([
        call(mock_runner, 'git add', ['git', 'add', '.'], fatal=True),
        # --- FIXED: fatal=False for commit ---
        call(mock_runner, 'git commit', ['git', 'commit', '-m', commit_msg], fatal=False),
        call(mock_runner, 'git push', ['git', 'push', '-u', 'origin', 'main'], fatal=True)
    ])
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60)
    ], any_order=False)
    # No success log on push failure (early return)
    assert not any('committed & pushed' in str(args) for args, _ in mock_runner.logger.info.call_args_list)

