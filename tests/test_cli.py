# tests/test_cli.py

"""Integration tests for CLI entrypoint."""

import sys
from unittest.mock import patch, Mock
import pytest
from pathlib import Path

from routine_workflow.cli import parse_arguments, main
from routine_workflow.config import WorkflowConfig
from routine_workflow.runner import WorkflowRunner


@patch("routine_workflow.cli.WorkflowRunner")
@patch("routine_workflow.cli.WorkflowConfig.from_args")
def test_main(mock_from_args: Mock, mock_runner: Mock):
    """Test main orchestrates config + runner."""
    mock_cfg = Mock(spec=WorkflowConfig)
    mock_from_args.return_value = mock_cfg
    mock_runner.return_value.run.return_value = 0

    with patch.object(sys, "argv", ["prog", "--dry-run"]):
        result = main()

    assert result == 0
    mock_from_args.assert_called_once()
    mock_runner.assert_called_once_with(mock_cfg)
    mock_runner.return_value.run.assert_called_once()


def test_parse_arguments_defaults():
    """Test arg parsing with defaults."""
    with patch.object(sys, "argv", ["prog"]):
        args = parse_arguments()

    assert args.dry_run is False
    assert args.project_root == Path.cwd()


def test_parse_arguments_custom():
    """Test custom args."""
    with patch.object(sys, "argv", ["prog", "--dry-run", "--workers", "2"]):
        args = parse_arguments()

    assert args.dry_run is True
    assert args.workers == 2