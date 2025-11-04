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
    return runner


def test_commit_hygiene_skip_dry_run(mock_runner: Mock, tmp_path: Path):
    """Test skip if dry_run=True."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        clean_script=tmp_path / "clean.py",
        backup_script=tmp_path / "backup.py",
        create_dump_script=tmp_path / "dump.sh",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=True,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=True,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config

    result = commit_hygiene(mock_runner)

    assert result is True
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60),
        call('Git skipped (dry-run, disabled, or missing git)')
    ], any_order=False)


def test_commit_hygiene_skip_disabled(mock_runner: Mock, tmp_path: Path):
    """Test skip if git_push=False."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        clean_script=tmp_path / "clean.py",
        backup_script=tmp_path / "backup.py",
        create_dump_script=tmp_path / "dump.sh",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=False,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config

    result = commit_hygiene(mock_runner)

    assert result is True
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60),
        call('Git skipped (dry-run, disabled, or missing git)')
    ], any_order=False)


@patch('routine_workflow.steps.step6.cmd_exists')
def test_commit_hygiene_skip_missing_git(mock_cmd_exists, mock_runner: Mock, tmp_path: Path):
    """Test skip if git not found."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        clean_script=tmp_path / "clean.py",
        backup_script=tmp_path / "backup.py",
        create_dump_script=tmp_path / "dump.sh",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=True,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_cmd_exists.return_value = False

    result = commit_hygiene(mock_runner)

    assert result is True
    mock_cmd_exists.assert_called_once_with('git')
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60),
        call('Git skipped (dry-run, disabled, or missing git)')
    ], any_order=False)


@patch('routine_workflow.steps.step6.run_command')
@patch('routine_workflow.steps.step6.datetime')
def test_commit_hygiene_full_success_with_changes(mock_datetime, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test full success: add/commit/push all succeed (changes present)."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        clean_script=tmp_path / "clean.py",
        backup_script=tmp_path / "backup.py",
        create_dump_script=tmp_path / "dump.sh",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=True,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_datetime.now.return_value.strftime.return_value = '2025-11-03 12:00:00'
    commit_msg = 'routine_hygiene: 2025-11-03 12:00:00'
    mock_run.side_effect = [True, True, True]  # add, commit (success), push

    with patch('routine_workflow.steps.step6.cmd_exists', return_value=True):
        result = commit_hygiene(mock_runner)

    assert result is True
    mock_datetime.now.assert_called_once()
    mock_run.assert_has_calls([
        call(mock_runner, 'git add', ['git', 'add', '.'], fatal=True),
        call(mock_runner, 'git commit', ['git', 'commit', '-m', commit_msg], fatal=True),
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
def test_commit_hygiene_success_no_changes(mock_datetime, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test success: add succeeds, commit fails (no changes), push succeeds."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        clean_script=tmp_path / "clean.py",
        backup_script=tmp_path / "backup.py",
        create_dump_script=tmp_path / "dump.sh",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=True,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_datetime.now.return_value.strftime.return_value = '2025-11-03 12:00:00'
    commit_msg = 'routine_hygiene: 2025-11-03 12:00:00'
    mock_run.side_effect = [True, False, True]  # add success, commit fails (no changes), push success

    with patch('routine_workflow.steps.step6.cmd_exists', return_value=True):
        result = commit_hygiene(mock_runner)

    assert result is True
    mock_run.assert_has_calls([
        call(mock_runner, 'git add', ['git', 'add', '.'], fatal=True),
        call(mock_runner, 'git commit', ['git', 'commit', '-m', commit_msg], fatal=True),
        call(mock_runner, 'git push', ['git', 'push', '-u', 'origin', 'main'], fatal=True)
    ])
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60),
        call('No changes to commit; snapshot up-to-date')
    ], any_order=False)


@patch('routine_workflow.steps.step6.run_command')
@patch('routine_workflow.steps.step6.datetime')
def test_commit_hygiene_add_failure(mock_datetime, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test early failure on git add."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        clean_script=tmp_path / "clean.py",
        backup_script=tmp_path / "backup.py",
        create_dump_script=tmp_path / "dump.sh",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=True,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_run.return_value = False  # add fails

    with patch('routine_workflow.steps.step6.cmd_exists', return_value=True):
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
def test_commit_hygiene_push_failure(mock_datetime, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test failure on push (after add/commit success)."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        clean_script=tmp_path / "clean.py",
        backup_script=tmp_path / "backup.py",
        create_dump_script=tmp_path / "dump.sh",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=True,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_datetime.now.return_value.strftime.return_value = '2025-11-03 12:00:00'
    commit_msg = 'routine_hygiene: 2025-11-03 12:00:00'
    mock_run.side_effect = [True, True, False]  # add, commit success, push fails

    with patch('routine_workflow.steps.step6.cmd_exists', return_value=True):
        result = commit_hygiene(mock_runner)

    assert result is False
    mock_run.assert_has_calls([
        call(mock_runner, 'git add', ['git', 'add', '.'], fatal=True),
        call(mock_runner, 'git commit', ['git', 'commit', '-m', commit_msg], fatal=True),
        call(mock_runner, 'git push', ['git', 'push', '-u', 'origin', 'main'], fatal=True)
    ])
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6: Commit hygiene snapshot to git'),
        call('=' * 60)
    ], any_order=False)
    # No success log on push failure (early return)
    assert not any('committed & pushed' in str(args) for args, _ in mock_runner.logger.info.call_args_list)