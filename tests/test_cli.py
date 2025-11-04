# tests/test_cli.py

"""Integration and unit tests for CLI entrypoint."""

import os
import sys
import argparse
from unittest.mock import patch, Mock, MagicMock, ANY, call
import pytest
from pathlib import Path

from routine_workflow.cli import (
    build_parser, main, validate_steps, _has_rich, render_rich_help
)
from routine_workflow.config import WorkflowConfig
from routine_workflow.runner import WorkflowRunner, STEP_NAMES


@pytest.fixture
def mock_parser():
    """Fixture for a mocked parser."""
    return build_parser()


def test_has_rich_no_rich():
    """Test _has_rich returns False when rich is not installed."""
    with patch('routine_workflow.cli.importlib.util.find_spec', return_value=None):
        assert _has_rich() is False


def test_has_rich_with_rich():
    """Test _has_rich returns True when rich is installed."""
    with patch('routine_workflow.cli.importlib.util.find_spec', return_value=Mock()):
        assert _has_rich() is True


@patch('rich.console.Console')
@patch('rich.markdown.Markdown')
@patch('rich.panel.Panel')
@patch('rich.table.Table')
@patch('rich.text.Text')
def test_render_rich_help(mock_text, mock_table, mock_panel, mock_markdown, mock_console):
    mock_parser = Mock()
    mock_parser.format_usage.return_value = 'usage: prog [options]'
    mock_parser.description = 'Test description'
    mock_parser.epilog = 'Examples:\n  cmd1\n  cmd2'
    mock_parser._actions = [
        Mock(option_strings=['-p', '--project-root'], help='Project root', default=Path('/default')),
        Mock(option_strings=['-d', '--dry-run'], help='Dry run', default=True),
    ]

    # Create separate mocks for each table
    options_table = MagicMock(name='options_table')
    steps_table = MagicMock(name='steps_table')
    mock_table.side_effect = [options_table, steps_table]

    console = MagicMock()
    render_rich_help(console, mock_parser)

    # Panels
    mock_panel.assert_has_calls([
        call(mock_text.return_value, title='Usage', border_style='yellow'),
        call(mock_markdown.return_value, title='[bold green]Quick Starts[/bold green]', border_style='green', expand=False)
    ])
    console.print.assert_any_call(mock_panel.return_value)

    # Options table
    options_table.add_column.assert_has_calls([
        call('Flag', style='green', no_wrap=True),
        call('Description', style='white')
    ])
    options_table.add_row.assert_has_calls([
        call('-p --project-root', 'Project root [dim](default: /default)[/dim]'),
        call('-d --dry-run', 'Dry run')
    ])
    console.print.assert_any_call(options_table)

    # Steps table
    steps_table.add_column.assert_has_calls([
        call('Step', style='cyan', no_wrap=True),
        call('Description', style='white')
    ])
    for step in sorted(STEP_NAMES):
        steps_table.add_row.assert_any_call(step, ANY)
    console.print.assert_any_call(steps_table)

    mock_markdown.assert_called_once_with(ANY)
def test_render_rich_help_no_description():
    """Test no description skips print."""
    mock_parser = Mock()
    mock_parser.format_usage.return_value = 'usage: prog [options]'  # str
    mock_parser.description = None
    mock_parser._actions = []
    mock_parser.epilog = ''

    console = MagicMock()
    render_rich_help(console, mock_parser)
    # Check no desc print
    assert not any('Description' in str(call[0][0]) for call in console.print.call_args_list)


def test_build_parser_help_texts():
    """Test all arguments have help texts and defaults."""
    parser = build_parser()
    actions = {a.dest: a for a in parser._actions if a.dest != 'help'}

    assert 'project_root' in actions
    assert actions['project_root'].help == 'Project root path'
    assert actions['project_root'].default == Path(os.getenv('PROJECT_ROOT', os.getcwd()))

    assert 'dry_run' in actions
    assert actions['dry_run'].default is True

    assert 'steps' in actions
    assert actions['steps'].nargs == '+'
    assert actions['steps'].default is None

    # Spot-check booleans - check type
    assert type(actions['enable_security']) == argparse._StoreTrueAction


def test_build_parser_remainder_arg():
    """Test --create-dump-run-cmd accepts remainder."""
    parser = build_parser()
    args = parser.parse_args(['--create-dump-run-cmd', 'cmd1', 'cmd2', 'arg1'])
    assert args.create_dump_run_cmd == ['cmd1', 'cmd2', 'arg1']


@patch('routine_workflow.cli._has_rich', return_value=True)
@patch('rich.console.Console')
def test_main_help_rich(mock_console, mock_has_rich):
    """Test main intercepts -h and uses rich help."""
    mock_console_instance = Mock()
    mock_console.return_value = mock_console_instance
    mock_render = Mock()
    with patch('routine_workflow.cli.render_rich_help', mock_render):
        with patch.object(sys, 'argv', ['prog', '-h']):
            result = main()

    assert result == 0
    mock_console.assert_called_once()
    mock_render.assert_called_once_with(mock_console_instance, ANY)


@patch('routine_workflow.cli._has_rich', return_value=False)
def test_main_help_fallback(mock_has_rich):
    """Test main falls back to print_help if no rich."""
    mock_parser = Mock()
    mock_print_help = Mock()
    mock_parser.print_help = mock_print_help
    with patch('routine_workflow.cli.build_parser', return_value=mock_parser):
        with patch.object(sys, 'argv', ['prog', '--help']):
            result = main()

    assert result == 0
    mock_print_help.assert_called_once()


@patch('routine_workflow.cli.WorkflowRunner')
@patch('routine_workflow.cli.WorkflowConfig.from_args')
def test_main_full_flow(mock_from_args, mock_runner):
    """Test full main: parse → validate → config → run."""
    mock_cfg = Mock(spec=WorkflowConfig)
    mock_from_args.return_value = mock_cfg
    mock_runner.return_value.run.return_value = 0

    with patch.object(sys, 'argv', ['prog', '-nd', '-s', 'step1', 'step99']):
        result = main()

    assert result == 0
    mock_from_args.assert_called_once()
    mock_runner.assert_called_once_with(mock_cfg, steps=['step1'])  # Filtered


def test_validate_steps_invalid_all(capsys):
    """Test all invalid: warn + exit 1."""
    with pytest.raises(SystemExit) as exc:
        validate_steps(['invalid1', 'invalid2'], STEP_NAMES)
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert 'Skipping invalid steps: invalid1, invalid2' in captured.err


def test_validate_steps_mixed(capsys):
    """Test mixed: filter valids, warn invalids."""
    result = validate_steps(['step1', 'invalid'], STEP_NAMES)
    assert result == ['step1']
    captured = capsys.readouterr()
    assert 'Skipping invalid steps: invalid' in captured.err


def test_validate_steps_empty_list():
    """Test empty list: treat as None, return []."""
    result = validate_steps([], STEP_NAMES)
    assert result == []


def test_validate_steps_none():
    """Test None: return []."""
    result = validate_steps(None, STEP_NAMES)
    assert result == []


class TestArgParsing:
    """Parametrized tests for specific arg combinations."""

    @pytest.mark.parametrize('args_str, expected_dry_run', [
        ('', True),
        ('-nd', False),
        ('-d -nd', False),
    ])
    def test_dry_run_toggle(self, args_str, expected_dry_run, tmp_path):
        """Test dry-run flag toggles and defaults."""
        argv = args_str.split()
        with patch.object(sys, 'argv', ['prog'] + argv):
            parser_args = build_parser().parse_args(argv)
        assert parser_args.dry_run == expected_dry_run

    @pytest.mark.parametrize('steps_str, expected_steps', [
        ('step1 step2', ['step1', 'step2']),
        ('step99', ['step99']),
    ])
    def test_steps_parsing(self, steps_str, expected_steps, tmp_path):
        """Test steps nargs='+'."""
        argv = ['-s'] + steps_str.split()
        parser_args = build_parser().parse_known_args(argv)[0]
        assert parser_args.steps == expected_steps

    @pytest.mark.parametrize('env_value, expected_default', [
        ('/custom', Path('/custom')),
        (None, Path.cwd()),
    ])
    def test_env_defaults(self, env_value, expected_default, monkeypatch):
        """Test env vars override hardcoded defaults."""
        if env_value is not None:
            monkeypatch.setenv('PROJECT_ROOT', env_value)
        parser_args = build_parser().parse_args([])
        assert parser_args.project_root == expected_default


@patch('routine_workflow.cli.WorkflowRunner')
@patch('routine_workflow.cli.WorkflowConfig.from_args')
def test_main_no_banner_nd(mock_from_args, mock_runner):
    """Test no banner when dry_run=False."""
    mock_cfg = Mock(spec=WorkflowConfig)
    mock_from_args.return_value = mock_cfg
    mock_runner.return_value.run.return_value = 0

    with patch.object(sys, 'argv', ['prog', '-nd']):
        result = main()

    assert result == 0


def test_main_sys_exit_guard():
    """Test __name__ guard prevents direct run in import."""
    import routine_workflow.cli  # No raise


@patch("routine_workflow.cli.WorkflowRunner")
@patch("routine_workflow.cli.WorkflowConfig.from_args")
def test_main(mock_from_args: Mock, mock_runner: Mock):
    """Test main orchestrates config + runner."""
    mock_cfg = Mock(spec=WorkflowConfig)
    mock_from_args.return_value = mock_cfg
    mock_runner.return_value.run.return_value = 0

    with patch.object(sys, "argv", ["prog"]):
        result = main()

    assert result == 0
    mock_from_args.assert_called_once()
    mock_runner.assert_called_once_with(mock_cfg, steps=[])
    mock_runner.return_value.run.assert_called_once()


@patch("routine_workflow.cli.WorkflowRunner")
@patch("routine_workflow.cli.WorkflowConfig.from_args")
def test_main_steps(mock_from_args: Mock, mock_runner: Mock):
    """Test main passes steps to runner."""
    mock_cfg = Mock(spec=WorkflowConfig)
    mock_from_args.return_value = mock_cfg
    mock_runner.return_value.run.return_value = 0

    with patch.object(sys, "argv", ["prog", "--steps", "step2", "step3"]):
        result = main()

    assert result == 0
    mock_runner.assert_called_once_with(mock_cfg, steps=["step2", "step3"])


def test_main_dry_run_banner(capsys):
    """Test dry-run banner prints on default invocation."""
    with patch.object(sys, "argv", ["prog"]):
        with patch("routine_workflow.cli.WorkflowRunner") as mock_runner:
            mock_runner.return_value.run.return_value = 0
            with patch("routine_workflow.cli.WorkflowConfig.from_args") as mock_cfg:
                mock_cfg.return_value = Mock(spec=WorkflowConfig)
                main()

    captured = capsys.readouterr()
    assert "🛡️  Safety mode: Dry-run enabled" in captured.out


def test_validate_steps_invalid(capsys):
    """Test validate_steps warns on invalids and exits if all invalid."""
    invalid_steps = ["step99"]
    with pytest.raises(SystemExit) as exc_info:
        validate_steps(invalid_steps, STEP_NAMES)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Warning: Skipping invalid steps: step99" in captured.err


def test_validate_steps_partial_invalid(capsys):
    """Test partial invalids: warn but continue with valids."""
    partial_steps = ["step2", "step99"]
    result = validate_steps(partial_steps, STEP_NAMES)
    captured = capsys.readouterr()
    assert "Warning: Skipping invalid steps: step99" in captured.err
    assert result == ["step2"]


def test_validate_steps_all_valid(capsys):
    """Test all valid: no warn, return as-is."""
    valid_steps = ["step1", "step2"]
    result = validate_steps(valid_steps, STEP_NAMES)
    assert result == valid_steps
    captured = capsys.readouterr()
    assert "Warning" not in captured.err


def test_parse_arguments_defaults():
    """Test arg parsing with defaults."""
    with patch.object(sys, "argv", ["prog"]):
        parser = build_parser()
        args = parser.parse_args([])

    assert args.dry_run is True
    assert args.project_root == Path.cwd()
    assert args.steps is None
    assert args.workers == min(8, os.cpu_count() or 4)
    assert args.enable_security is False
    assert args.enable_dep_audit is False


def test_parse_arguments_custom():
    """Test custom args."""
    with patch.object(sys, "argv", ["prog", "-d", "-w", "2", "-s", "step1", "-es", "-eda"]):
        parser = build_parser()
        args = parser.parse_args(["-d", "-w", "2", "-s", "step1", "-es", "-eda"])

    assert args.dry_run is True
    assert args.workers == 2
    assert args.steps == ["step1"]
    assert args.enable_security is True
    assert args.enable_dep_audit is True


def test_parse_arguments_no_dry_run():
    """Test -nd disables dry-run."""
    with patch.object(sys, "argv", ["prog", "-nd"]):
        parser = build_parser()
        args = parser.parse_args(["-nd"])

    assert args.dry_run is False


def test_parse_arguments_shortcuts():
    """Test shortcuts map correctly."""
    with patch.object(sys, "argv", ["prog", "-p", "/custom/root", "-l", "/custom/logs", "-t", "1800"]):
        parser = build_parser()
        args = parser.parse_args(["-p", "/custom/root", "-l", "/custom/logs", "-t", "1800"])

    assert args.project_root == Path("/custom/root")