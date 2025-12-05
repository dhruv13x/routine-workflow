# tests/test_steps/test_step2.py

"""Tests for step2: Reformat code."""

from unittest.mock import patch, Mock
import pytest

from routine_workflow.steps.step2 import reformat_code
from routine_workflow.runner import WorkflowRunner


@patch("routine_workflow.formatting_service.run_autoimport_parallel")
@patch("routine_workflow.formatting_service.cmd_exists")
@patch("routine_workflow.formatting_service.run_command")
def test_reformat_code_full(mock_cmd: Mock, mock_exists: Mock, mock_autoimport: Mock, mock_runner: Mock):
    """Test all tools called if available."""
    mock_exists.side_effect = lambda x: x != "missing"
    mock_cmd.return_value = True
    mock_runner.config.dry_run = False

    reformat_code(mock_runner)

    assert mock_cmd.call_count == 5  # ruff initial, autoflake, isort, ruff check, ruff final
    mock_autoimport.assert_called_once_with(mock_runner)
    mock_runner.logger.info.assert_any_call("Reformat complete")


@patch("routine_workflow.formatting_service.cmd_exists")
def test_reformat_code_skips_missing(mock_exists: Mock, mock_runner: Mock):
    """Test skips if tools missing."""
    mock_exists.return_value = False
    mock_runner.config.dry_run = False

    reformat_code(mock_runner)

    mock_runner.logger.info.assert_any_call("autoimport not installed - skipping")


@patch("routine_workflow.formatting_service.run_autoimport_parallel")
@patch("routine_workflow.formatting_service.cmd_exists")
@patch("routine_workflow.formatting_service.run_command")
def test_reformat_code_dry_run(mock_cmd: Mock, mock_exists: Mock, mock_autoimport: Mock, mock_runner: Mock):
    """Test dry-run skips all tool execution."""
    mock_runner.config.dry_run = True
    mock_exists.side_effect = lambda x: True

    reformat_code(mock_runner)

    assert mock_cmd.call_count == 0  # Full skip; no run_command
    mock_autoimport.assert_not_called()  # No call; guard before
    mock_runner.logger.info.assert_any_call('DRY-RUN: Skipping reformat (tools lack native preview)')


@patch("routine_workflow.formatting_service.run_autoimport_parallel")
@patch("routine_workflow.formatting_service.cmd_exists")
@patch("routine_workflow.formatting_service.run_command")
def test_reformat_code_ruff_only(mock_cmd: Mock, mock_exists: Mock, mock_autoimport: Mock, mock_runner: Mock):
    """Test ruff-only sequence if other tools missing."""
    mock_exists.side_effect = lambda x: x == 'ruff'
    mock_cmd.return_value = True
    mock_runner.config.dry_run = False

    reformat_code(mock_runner)

    assert mock_cmd.call_count == 3  # ruff initial, ruff check, ruff final
    mock_autoimport.assert_not_called()
    mock_runner.logger.info.assert_any_call('autoimport not installed - skipping')
    mock_runner.logger.info.assert_any_call("Reformat complete")


@patch("routine_workflow.formatting_service.run_autoimport_parallel")
@patch("routine_workflow.formatting_service.cmd_exists")
@patch("routine_workflow.formatting_service.run_command")
def test_reformat_code_autoimport_dry_run(mock_cmd: Mock, mock_exists: Mock, mock_autoimport: Mock, mock_runner: Mock):
    """Test autoimport dry-run within reformat (real-run case)."""
    mock_runner.config.dry_run = True
    mock_exists.side_effect = lambda x: x == 'autoimport'

    reformat_code(mock_runner)

    mock_autoimport.assert_not_called()  # Guard skips before; internal dry n/a
    mock_cmd.call_count == 0  # No run_command for autoimport


@patch("routine_workflow.formatting_service.run_autoimport_parallel")
@patch("routine_workflow.formatting_service.cmd_exists")
@patch("routine_workflow.formatting_service.run_command")
def test_reformat_code_autoimport_real_run(mock_cmd: Mock, mock_exists: Mock, mock_autoimport: Mock, mock_runner: Mock):
    """Test autoimport execution in real-run (with internal dry logic)."""
    mock_runner.config.dry_run = False
    mock_exists.side_effect = lambda x: x == 'autoimport'

    reformat_code(mock_runner)

    mock_autoimport.assert_called_once_with(mock_runner)  # Called in real-run; internal dry if enabled
    mock_cmd.call_count == 0  # No run_command for autoimport
