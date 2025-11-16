# tests/test_steps/test_step5.py

"""Tests for step5: Generate dumps."""

from unittest.mock import patch, Mock
from pathlib import Path
import pytest

from routine_workflow.steps.step5 import generate_dumps
from routine_workflow.runner import WorkflowRunner
from routine_workflow.utils import cmd_exists, run_command


def test_generate_dumps_no_tool(mock_runner: Mock):
    """Test skip if create-dump not found."""
    mock_runner.config.dry_run = False
    with patch('routine_workflow.steps.step5.cmd_exists') as mock_exists:
        mock_exists.return_value = False

        generate_dumps(mock_runner)

    mock_runner.logger.warning.assert_called_once_with('create-dump not found - skipping generation')


@patch('routine_workflow.steps.step5.cmd_exists')
def test_generate_dumps_dry_run(mock_exists, mock_runner: Mock):
    """Test dry-run invokes tool with default dry estimation."""
    mock_runner.config.dry_run = True
    mock_runner.config.create_dump_run_cmd = ['create-dump', 'batch', 'run']  # Set to avoid attr error
    mock_exists.return_value = True

    generate_dumps(mock_runner)

    mock_runner.logger.info.assert_called_with('Code-dump generation completed successfully')  # Tool succeeds with default dry


@patch('routine_workflow.steps.step5.run_command')
@patch('routine_workflow.steps.step5.cmd_exists')
def test_generate_dumps_success(mock_exists, mock_run, mock_runner: Mock):
    """Test successful tool invocation."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.create_dump_run_cmd = ['create-dump', 'batch', 'run']
    mock_exists.return_value = True
    mock_run.return_value = True

    generate_dumps(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Batch generate code dumps', ['create-dump', 'batch', 'run', '-nd', '-y'],
        cwd=mock_runner.config.project_root, timeout=600.0, fatal=False
    )
    mock_runner.logger.info.assert_called_with('Code-dump generation completed successfully')


@patch('routine_workflow.steps.step5.run_command')
@patch('routine_workflow.steps.step5.cmd_exists')
def test_generate_dumps_failure(mock_exists, mock_run, mock_runner: Mock):
    """Test handles tool failure gracefully."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = False
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.create_dump_run_cmd = ['create-dump', 'batch', 'run']
    mock_exists.return_value = True
    mock_run.return_value = False

    generate_dumps(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Batch generate code dumps', ['create-dump', 'batch', 'run', '-nd'],
        cwd=mock_runner.config.project_root, timeout=600.0, fatal=False
    )
    mock_runner.logger.warning.assert_called_with('Code-dump generation failed or skipped')


@patch('routine_workflow.steps.step5.run_command')
@patch('routine_workflow.steps.step5.cmd_exists')
def test_generate_dumps_cmd_fallback(mock_exists, mock_run, mock_runner: Mock):
    """Test fallback cmd if create_dump_run_cmd not set."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = False
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.create_dump_run_cmd = None  # Trigger fallback
    mock_exists.return_value = True
    mock_run.return_value = True

    generate_dumps(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Batch generate code dumps', ['create-dump', 'batch', 'run', '--dirs', '., packages, packages/platform_core, packages/telethon_adapter_kit, services, services/forwarder_bot', '-nd'],
        cwd=mock_runner.config.project_root, timeout=600.0, fatal=False
    )


@patch('routine_workflow.steps.step5.run_command')
@patch('routine_workflow.steps.step5.cmd_exists')
def test_generate_dumps_no_yes(mock_exists, mock_run, mock_runner: Mock):
    """Test no -y flag if not auto_yes."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = False
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.create_dump_run_cmd = ['create-dump', 'batch', 'run']
    mock_exists.return_value = True
    mock_run.return_value = True

    generate_dumps(mock_runner)

    call_args = mock_run.call_args[0][2]
    assert '-y' not in call_args
    assert '-nd' in call_args


@patch('routine_workflow.steps.step5.cmd_exists')
def test_generate_dumps_fallback_dry_run(mock_exists, mock_runner: Mock):
    """Test fallback with dry-run."""
    mock_runner.config.dry_run = True
    mock_runner.config.create_dump_run_cmd = None
    mock_exists.return_value = True

    generate_dumps(mock_runner)

    mock_runner.logger.info.assert_called_with('Code-dump generation completed successfully')  # Tool succeeds with default dry


@patch('routine_workflow.steps.step5.run_command')
@patch('routine_workflow.steps.step5.cmd_exists')
def test_generate_dumps_fallback_failure(mock_exists, mock_run, mock_runner: Mock):
    """Test failure with fallback cmd."""
    mock_runner.config.dry_run = False
    mock_runner.config.auto_yes = True
    mock_runner.config.project_root = Path('/tmp/project')
    mock_runner.config.create_dump_run_cmd = None  # Trigger fallback
    mock_exists.return_value = True
    mock_run.return_value = False

    generate_dumps(mock_runner)

    mock_run.assert_called_once_with(
        mock_runner, 'Batch generate code dumps', ['create-dump', 'batch', 'run', '--dirs', '., packages, packages/platform_core, packages/telethon_adapter_kit, services, services/forwarder_bot', '-nd', '-y'],
        cwd=mock_runner.config.project_root, timeout=600.0, fatal=False
    )
    mock_runner.logger.warning.assert_called_with('Code-dump generation failed or skipped')
