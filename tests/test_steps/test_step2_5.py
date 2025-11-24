# tests/test_steps/test_step2_5.py

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
    mock_run.return_value = {"success": True, "stdout": "", "stderr": ""}

    with patch('routine_workflow.steps.step2_5.cmd_exists', return_value=True):
        result = run_tests(mock_runner)

    assert result is True
    # --- FIXED: Assert the new, complex command signature ---
    expected_cmd = [
        'pytest', '.',
        '-vv', '-s', '-ra', '--tb=long', '--showlocals',
        '--log-cli-level=DEBUG', '--setup-show', '--durations=10',
        '--timeout=15',
        '--cov-report=term-missing', '--cov-report=html', '--cov=.', '.',
        '--cov-fail-under', '85'
    ]
    mock_run.assert_called_once_with(
        mock_runner, 'pytest suite', expected_cmd,
        cwd=config.project_root, timeout=1800.0, fatal=False, stream=True
    )
    mock_runner.logger.info.assert_called_with('Tests passed (coverage >= 85%)')
    mock_runner.logger.error.assert_not_called()


@patch('routine_workflow.steps.step2_5.run_command')
def test_run_tests_failure(mock_run, mock_runner: Mock, tmp_path: Path):
    """Test failure logs warning (not error) and returns False."""
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
    mock_run.return_value = {"success": False, "stdout": "", "stderr": "Test failed"}

    with patch('routine_workflow.steps.step2_5.cmd_exists', return_value=True):
        result = run_tests(mock_runner)

    assert result is False
    # --- FIXED: Implementation now logs a WARNING, not an ERROR ---
    mock_runner.logger.warning.assert_called_once_with('Tests failed (flakes detected) - continuing workflow')
    mock_runner.logger.error.assert_not_called()
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
    """Test dry-run uses --collect-only."""
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
    # --- FIXED: Assert the new dry-run command ---
    expected_cmd = ['pytest', '.', '--collect-only']
    mock_run.assert_called_once_with(
        mock_runner, 'pytest suite preview', expected_cmd,
        cwd=config.project_root, timeout=60.0, fatal=False, stream=True
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
    # --- FIXED: Assert new command, but without coverage fail flag ---
    expected_cmd = [
        'pytest', '.',
        '-vv', '-s', '-ra', '--tb=long', '--showlocals',
        '--log-cli-level=DEBUG', '--setup-show', '--durations=10',
        '--timeout=15',
        '--cov-report=term-missing', '--cov-report=html', '--cov=.', '.'
        # No '--cov-fail-under'
    ]
    mock_run.assert_called_once_with(
        mock_runner, 'pytest suite', expected_cmd,
        cwd=config.project_root, timeout=1800.0, fatal=False, stream=True
    )
    mock_runner.logger.info.assert_called_with('Tests passed (coverage >= 0%)')


@patch('routine_workflow.steps.step2_5.run_command')
def test_run_tests_single_worker(mock_run, mock_runner: Mock, tmp_path: Path):
    """Test no -n if workers=1 (and no -n in new command anyway)."""
    config = WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "test.log",
        lock_dir=tmp_path / "lock",
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
    # --- FIXED: Assert the new command (which has no -n logic) ---
    expected_cmd = [
        'pytest', '.',
        '-vv', '-s', '-ra', '--tb=long', '--showlocals',
        '--log-cli-level=DEBUG', '--setup-show', '--durations=10',
        '--timeout=15',
        '--cov-report=term-missing', '--cov-report=html', '--cov=.', '.',
        '--cov-fail-under', '85'
    ]
    mock_run.assert_called_once_with(
        mock_runner, 'pytest suite', expected_cmd,
        cwd=config.project_root, timeout=1800.0, fatal=False, stream=True
    )
    mock_runner.logger.info.assert_called_with('Tests passed (coverage >= 85%)')
