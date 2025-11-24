# tests/test_steps/test_step3_5.py

"""Tests for step3_5: Security vulnerability scan."""

from unittest.mock import Mock, patch, call
import pytest
from pathlib import Path

from routine_workflow.steps.step3_5 import security_scan
from routine_workflow.runner import WorkflowRunner
from routine_workflow.config import WorkflowConfig
from routine_workflow.utils import cmd_exists, run_command


@pytest.fixture
def mock_runner(tmp_path: Path):
    """Mock runner with config and logger."""
    runner = Mock(spec=WorkflowRunner)
    runner.logger = Mock()  # Explicit for dynamic attr
    return runner


def test_security_scan_skip_dry_run(mock_runner: Mock, tmp_path: Path):
    """Test skip if dry_run=True."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=True,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=False,
        enable_security=True,  # But dry_run overrides
        enable_dep_audit=False,
    )
    mock_runner.config = config

    result = security_scan(mock_runner)

    assert result is True
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 3.5: Security vulnerability scan'),
        call('=' * 60),
        call('Security scan skipped (dry-run or disabled)')
    ], any_order=False)


def test_security_scan_skip_disabled(mock_runner: Mock, tmp_path: Path):
    """Test skip if enable_security=False."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
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

    result = security_scan(mock_runner)

    assert result is True
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 3.5: Security vulnerability scan'),
        call('=' * 60),
        call('Security scan skipped (dry-run or disabled)')
    ], any_order=False)


@patch('routine_workflow.steps.step3_5.run_command')
@patch('routine_workflow.steps.step3_5.cmd_exists')
def test_security_scan_both_tools_missing(mock_cmd_exists, mock_run, mock_runner: Mock, tmp_path: Path):
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=False,
        enable_security=True,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_cmd_exists.side_effect = [False, False]  # bandit, safety

    result = security_scan(mock_runner)

    assert result is True
    mock_cmd_exists.assert_has_calls([call('bandit'), call('safety')])
    mock_run.assert_not_called()
    mock_runner.logger.warning.assert_has_calls([
        call('bandit not found - skipping bandit scan'),
        call('safety not found - skipping safety scan')
    ])
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 3.5: Security vulnerability scan'),
        call('=' * 60),
        call('Security scans passed - no critical vulns found')
    ], any_order=False)


@patch('routine_workflow.steps.step3_5.run_command')
@patch('routine_workflow.steps.step3_5.cmd_exists')
def test_security_scan_bandit_missing_safety_success(mock_cmd_exists, mock_run, mock_runner: Mock, tmp_path: Path):
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=False,
        enable_security=True,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_cmd_exists.side_effect = [False, True]  # bandit missing, safety exists
    mock_run.return_value = True

    result = security_scan(mock_runner)

    assert result is True
    mock_cmd_exists.assert_has_calls([call('bandit'), call('safety')])
    mock_run.assert_called_once_with(
        mock_runner, 'safety security scan',
        ['safety', 'check', '--full-report', '--json'],
        cwd=config.project_root, timeout=180.0, fatal=True
    )
    mock_runner.logger.warning.assert_called_once_with('bandit not found - skipping bandit scan')
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 3.5: Security vulnerability scan'),
        call('=' * 60),
        call('Security scans passed - no critical vulns found')
    ], any_order=False)


@patch('routine_workflow.steps.step3_5.run_command')
@patch('routine_workflow.steps.step3_5.cmd_exists')
def test_security_scan_safety_missing_bandit_success(mock_cmd_exists, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test safety missing, bandit runs success."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=False,
        enable_security=True,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_cmd_exists.side_effect = [True, False]  # bandit exists, safety missing
    mock_run.return_value = True

    result = security_scan(mock_runner)

    assert result is True
    mock_cmd_exists.assert_has_calls([call('bandit'), call('safety')])
    mock_run.assert_called_once_with(
        mock_runner, 'bandit security scan',
        ['bandit', '-r', '.', '-f', 'json', '--exclude', 'venv,__pycache__,node_modules', '--quiet'],
        cwd=config.project_root, timeout=180.0, fatal=True
    )
    mock_runner.logger.warning.assert_called_once_with('safety not found - skipping safety scan')
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 3.5: Security vulnerability scan'),
        call('=' * 60),
        call('Security scans passed - no critical vulns found')
    ], any_order=False)


@patch('routine_workflow.steps.step3_5.run_command')
@patch('routine_workflow.steps.step3_5.cmd_exists')
def test_security_scan_both_tools_success(mock_cmd_exists, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test both tools run and succeed."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=False,
        enable_security=True,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_cmd_exists.side_effect = [True, True]  # Both exist
    mock_run.return_value = True

    result = security_scan(mock_runner)

    assert result is True
    mock_cmd_exists.assert_has_calls([call('bandit'), call('safety')])
    mock_run.assert_has_calls([
        call(
            mock_runner, 'bandit security scan',
            ['bandit', '-r', '.', '-f', 'json', '--exclude', 'venv,__pycache__,node_modules', '--quiet'],
            cwd=config.project_root, timeout=180.0, fatal=True
        ),
        call(
            mock_runner, 'safety security scan',
            ['safety', 'check', '--full-report', '--json'],
            cwd=config.project_root, timeout=180.0, fatal=True
        )
    ])
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 3.5: Security vulnerability scan'),
        call('=' * 60),
        call('Security scans passed - no critical vulns found')
    ], any_order=False)
    mock_runner.logger.warning.assert_not_called()
    mock_runner.logger.error.assert_not_called()


@patch('routine_workflow.steps.step3_5.run_command')
@patch('routine_workflow.steps.step3_5.cmd_exists')
def test_security_scan_bandit_failure(mock_cmd_exists, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test failure on bandit; aborts early."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=False,
        enable_security=True,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_cmd_exists.side_effect = [True]  # Only bandit called
    mock_run.return_value = False  # bandit fails

    result = security_scan(mock_runner)

    assert result is False
    mock_cmd_exists.assert_called_once_with('bandit')
    mock_run.assert_called_once_with(
        mock_runner, 'bandit security scan',
        ['bandit', '-r', '.', '-f', 'json', '--exclude', 'venv,__pycache__,node_modules', '--quiet'],
        cwd=config.project_root, timeout=180.0, fatal=True
    )
    mock_runner.logger.error.assert_called_once_with('bandit scan failed - aborting workflow')
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 3.5: Security vulnerability scan'),
        call('=' * 60)
    ], any_order=False)
    # Success log not called (early return)
    assert not any('Security scans passed' in str(args) for args, _ in mock_runner.logger.info.call_args_list)
    # Safety not reached


@patch('routine_workflow.steps.step3_5.run_command')
@patch('routine_workflow.steps.step3_5.cmd_exists')
def test_security_scan_safety_failure(mock_cmd_exists, mock_run, mock_runner: Mock, tmp_path: Path):
    """Test failure on safety after bandit success; aborts."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
        fail_on_backup=False,
        auto_yes=False,
        dry_run=False,
        max_workers=4,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=False,
        enable_security=True,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_cmd_exists.side_effect = [True, True]  # Both exist
    mock_run.side_effect = [True, False]  # bandit succeeds, safety fails

    result = security_scan(mock_runner)

    assert result is False
    mock_cmd_exists.assert_has_calls([call('bandit'), call('safety')])
    mock_run.assert_has_calls([
        call(
            mock_runner, 'bandit security scan',
            ['bandit', '-r', '.', '-f', 'json', '--exclude', 'venv,__pycache__,node_modules', '--quiet'],
            cwd=config.project_root, timeout=180.0, fatal=True
        ),
        call(
            mock_runner, 'safety security scan',
            ['safety', 'check', '--full-report', '--json'],
            cwd=config.project_root, timeout=180.0, fatal=True
        )
    ])
    mock_runner.logger.error.assert_called_once_with('safety scan failed - aborting workflow')
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 3.5: Security vulnerability scan'),
        call('=' * 60)
    ], any_order=False)
    # Success log not called (early return)
    assert not any('Security scans passed' in str(args) for args, _ in mock_runner.logger.info.call_args_list)
