"""Tests for step2_5: Run pytest suite."""

from unittest.mock import Mock, patch, call
import pytest
from pathlib import Path

from routine_workflow.steps.step2_5 import run_tests
from routine_workflow.runner import WorkflowRunner
from routine_workflow.config import WorkflowConfig
from routine_workflow.utils import run_command, cmd_exists


@pytest.fixture
def mock_runner(tmp_path: Path):
    """Mock runner with config and logger."""
    runner = Mock(spec=WorkflowRunner)
    runner.logger = Mock()  # Explicit for dynamic attr
    return runner


def test_run_tests_pytest_missing(mock_runner: Mock, tmp_path: Path):
    """Test skip if pytest not found."""
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
        test_cov_threshold=85,  # Unused in skip path
        git_push=False,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    with patch('routine_workflow.steps.step2_5.cmd_exists', return_value=False):
        result = run_tests(mock_runner)

    assert result is True
    mock_runner.logger.warning.assert_called_once_with('pytest not found - skipping tests')
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 2.5: Run pytest suite'),
        call('=' * 60)
    ], any_order=False)


@patch('routine_workflow.steps.step2_5.run_command')
def test_run_tests_success(mock_run, mock_runner: Mock, tmp_path: Path):
    """Test success path with full cmd."""
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
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    with patch('routine_workflow.steps.step2_5.cmd_exists', return_value=True):
        result = run_tests(mock_runner)

    assert result is True
    mock_run.assert_called_once_with(
        mock_runner, 'pytest suite', [
            'pytest', '.', '--cov=src', '--cov-report=term-missing', '-q',
            '--cov-fail-under', '85', '-n', '4'
        ],
        cwd=config.project_root, timeout=300.0, fatal=True
    )
    mock_runner.logger.info.assert_called_with('Tests passed (coverage >= 85%)')
    mock_runner.logger.error.assert_not_called()


@patch('routine_workflow.steps.step2_5.run_command')
def test_run_tests_failure(mock_run, mock_runner: Mock, tmp_path: Path):
    """Test failure halts with error log."""
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
    mock_run.return_value = {"success": False, "stdout": "", "stderr": "Test failed"}

    with patch('routine_workflow.steps.step2_5.cmd_exists', return_value=True):
        result = run_tests(mock_runner)

    assert result is False
    mock_runner.logger.error.assert_called_once_with('Tests failed - aborting workflow')
    # Headers called; success msg not
    mock_runner.logger.info.assert_has_calls([
        call('=' * 60),
        call('STEP 2.5: Run pytest suite'),
        call('=' * 60)
    ], any_order=False)
    # No success log on failure
    assert not any('Tests passed' in str(args) for args, _ in mock_runner.logger.info.call_args_list)


@patch('routine_workflow.steps.step2_5.run_command')
def test_run_tests_dry_run(mock_run, mock_runner: Mock, tmp_path: Path):
    """Test dry-run uses --collect-only (no workers flag)."""
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
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_run.return_value = {
        "success": True,
        "stdout": "1682 tests collected in 10.91s",
        "stderr": ""
    }

    with patch('routine_workflow.steps.step2_5.cmd_exists', return_value=True):
        result = run_tests(mock_runner)

    assert result is True
    mock_run.assert_called_once_with(
        mock_runner, 'pytest suite', [
            'pytest', '.', '--cov=src', '--cov-report=term-missing', '-q',
            '--cov-fail-under', '85', '--collect-only'  # No -n in dry-run
        ],
        cwd=config.project_root, timeout=300.0, fatal=True
    )
    mock_runner.logger.info.assert_called_with('Test suite preview: 1682 tests discovered')


@patch('routine_workflow.steps.step2_5.run_command')
def test_run_tests_no_threshold(mock_run, mock_runner: Mock, tmp_path: Path):
    """Test no --cov-fail-under if threshold=0."""
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
        max_workers=1,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=0,
        git_push=False,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    with patch('routine_workflow.steps.step2_5.cmd_exists', return_value=True):
        result = run_tests(mock_runner)

    assert result is True
    mock_run.assert_called_once_with(
        mock_runner, 'pytest suite', [
            'pytest', '.', '--cov=src', '--cov-report=term-missing', '-q'
        ],
        cwd=config.project_root, timeout=300.0, fatal=True
    )
    mock_runner.logger.info.assert_called_with('Tests passed (coverage >= 0%)')


@patch('routine_workflow.steps.step2_5.run_command')
def test_run_tests_single_worker(mock_run, mock_runner: Mock, tmp_path: Path):
    """Test no -n if workers=1."""
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
        max_workers=1,
        workflow_timeout=0,
        exclude_patterns=[],
        test_cov_threshold=85,
        git_push=False,
        enable_security=False,
        enable_dep_audit=False,
    )
    mock_runner.config = config
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    with patch('routine_workflow.steps.step2_5.cmd_exists', return_value=True):
        result = run_tests(mock_runner)

    assert result is True
    mock_run.assert_called_once_with(
        mock_runner, 'pytest suite', [
            'pytest', '.', '--cov=src', '--cov-report=term-missing', '-q',
            '--cov-fail-under', '85'
        ],
        cwd=config.project_root, timeout=300.0, fatal=True
    )
    mock_runner.logger.info.assert_called_with('Tests passed (coverage >= 85%)')