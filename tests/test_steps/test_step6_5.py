# tests/test_steps/test_step6_5.py

"""Tests for step6_5: Dependency vulnerability audit."""

from unittest.mock import Mock, patch, call  # Added call import
import pytest
from pathlib import Path

from routine_workflow.steps.step6_5 import dep_audit
from routine_workflow.runner import WorkflowRunner
from routine_workflow.config import WorkflowConfig
from routine_workflow.utils import cmd_exists, run_command


@pytest.fixture
def mock_runner(tmp_path: Path):
    """Mock runner with config and logger."""
    runner = Mock(spec=WorkflowRunner)
    runner.logger = Mock()  # Explicit for dynamic attr
    return runner


def test_dep_audit_skip_dry_run(mock_runner: Mock, tmp_path: Path):
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
        git_push=False,
        enable_security=False,
        enable_dep_audit=True,  # But dry_run overrides
    )
    mock_runner.config = config

    result = dep_audit(mock_runner)

    assert result is True
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6.5: Dependency vulnerability audit'),
        call('=' * 60),
        call('Dep audit skipped (dry-run or disabled)')
    ], any_order=False)


def test_dep_audit_skip_disabled(mock_runner: Mock, tmp_path: Path):
    """Test skip if enable_dep_audit=False."""
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

    result = dep_audit(mock_runner)

    assert result is True
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6.5: Dependency vulnerability audit'),
        call('=' * 60),
        call('Dep audit skipped (dry-run or disabled)')
    ], any_order=False)


@patch('routine_workflow.steps.step6_5.cmd_exists')
def test_dep_audit_tool_missing(mock_cmd_exists, mock_runner: Mock, tmp_path: Path):
    """Test skip if pip-audit not found."""
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
        enable_dep_audit=True,
    )
    mock_runner.config = config
    mock_cmd_exists.return_value = False

    result = dep_audit(mock_runner)

    assert result is True
    mock_cmd_exists.assert_called_once_with('pip-audit')
    mock_runner.logger.warning.assert_called_once_with('pip-audit not found - skipping dep audit')
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6.5: Dependency vulnerability audit'),
        call('=' * 60)
    ], any_order=False)


@patch('routine_workflow.steps.step6_5.run_command')
@patch('routine_workflow.steps.step6_5.cmd_exists')
def test_dep_audit_success(mock_cmd_exists, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test audit runs and succeeds (no vulns)."""
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
        enable_dep_audit=True,
    )
    mock_runner.config = config
    mock_cmd_exists.return_value = True
    mock_run.return_value = True

    result = dep_audit(mock_runner)

    assert result is True
    mock_cmd_exists.assert_called_once_with('pip-audit')
    mock_run.assert_called_once_with(
        mock_runner, 'pip-audit dep scan',
        ['pip-audit', '--requirement', 'requirements.txt', '--format', 'json', '--ignore', 'vulnerability:low'],
        cwd=config.project_root, timeout=60.0, fatal=True
    )
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6.5: Dependency vulnerability audit'),
        call('=' * 60),
        call('Dep audit passed - no vulnerable dependencies')
    ], any_order=False)


@patch('routine_workflow.steps.step6_5.run_command')
@patch('routine_workflow.steps.step6_5.cmd_exists')
def test_dep_audit_failure(mock_cmd_exists, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test audit runs and fails (vulns detected)."""
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
        enable_dep_audit=True,
    )
    mock_runner.config = config
    mock_cmd_exists.return_value = True
    mock_run.return_value = False

    result = dep_audit(mock_runner)

    assert result is False
    mock_cmd_exists.assert_called_once_with('pip-audit')
    mock_run.assert_called_once_with(
        mock_runner, 'pip-audit dep scan',
        ['pip-audit', '--requirement', 'requirements.txt', '--format', 'json', '--ignore', 'vulnerability:low'],
        cwd=config.project_root, timeout=60.0, fatal=True
    )
    mock_runner.logger.error.assert_called_once_with('Dep audit failed - vulns detected in requirements.txt; review before commit')
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 6.5: Dependency vulnerability audit'),
        call('=' * 60)
    ], any_order=False)
    # No success log on failure
    assert not any('passed' in str(args) for args, _ in mock_runner.logger.info.call_args_list)
