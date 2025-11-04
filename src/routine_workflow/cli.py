# src/routine_workflow/cli.py

"""CLI argument parsing and main entrypoint for `routine-workflow`.

This module provides a curses-free argparse parser and an optional
rich-powered --help renderer (when rich is installed).
"""

import os
import sys
import argparse
import importlib.util
import textwrap
from pathlib import Path
from typing import List, Optional, Set

from .config import WorkflowConfig
from .runner import WorkflowRunner, STEP_NAMES


def _has_rich() -> bool:
    return importlib.util.find_spec("rich") is not None


def render_rich_help(console, parser: argparse.ArgumentParser) -> None:
    """Render a friendly --help using rich panels and tables.

    This mirrors the argparse data but prints it with richer formatting.
    """
    from rich.text import Text
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown

    # Usage (bold yellow box)
    usage = parser.format_usage()
    console.print(Panel(Text(usage, style="bold yellow"), title="Usage", border_style="yellow"))

    # Description
    description = parser.description
    if description:
        console.print(f"[bold magenta]Description:[/bold magenta] {description}")

    # Options Table (green flags, dim defaults)
    options_table = Table(title="[bold magenta]Options[/bold magenta]", show_header=True, header_style="bold cyan")
    options_table.add_column("Flag", style="green", no_wrap=True)
    options_table.add_column("Description", style="white")

    for action in parser._actions:
        if getattr(action, 'dest', None) == 'help':  # skip built-in help action
            continue
        # Build a succinct flag string (shorts + longs)
        flag_str = ' '.join(action.option_strings) if action.option_strings else action.dest.upper()
        desc = action.help or ''
        if (action.default is not argparse.SUPPRESS) and (action.default is not None) and (not isinstance(action.default, bool)):
            # Show non-boolean defaults inline (booleans are obvious from presence/absence)
            default = f" [dim](default: {action.default})[/dim]"
            desc += default
        options_table.add_row(flag_str, desc)

    console.print(options_table)

    # Steps Table (keys match STEP_NAMES with dots preserved)
    steps_table = Table(title="[bold magenta]Available Workflow Steps[/bold magenta]", show_header=True, header_style="bold cyan")
    steps_table.add_column("Step", style="cyan", no_wrap=True)
    steps_table.add_column("Description", style="white")
    step_descriptions = {
        "step1": "Delete old dumps (prune artifacts)",
        "step2": "Reformat code (autoimport + black)",
        "step2.5": "Optional: Run inline tests",
        "step3": "Clean caches (rm temps)",
        "step3.5": "Optional: Security scan (bandit)",
        "step4": "Backup project (tar/zip)",
        "step5": "Generate dumps (create-dump integration)",
        "step6": "Commit hygiene snapshot to git",
        "step6.5": "Optional: Dep vulnerability audit",
    }
    for step in sorted(STEP_NAMES):
        desc = step_descriptions.get(step, "Custom/undefined step")
        steps_table.add_row(step, desc)

    console.print(steps_table)

    # Examples Panel (render the parser epilog as Markdown code blocks)
    epilog_lines = [line.rstrip() for line in (parser.epilog or "").splitlines() if line.strip()]
    examples_content = "# Usage Examples\n"
    for line in epilog_lines:
        if line.startswith('#') or line.lower().startswith('examples:'):
            continue
        if line.startswith('routine-workflow'):
            examples_content += f"- ```bash\n{line}\n```\n"
        else:
            examples_content += f"{line}\n"

    examples_panel = Panel(
        Markdown(examples_content),
        title="[bold green]Quick Starts[/bold green]",
        border_style="green",
        expand=False,
    )
    console.print(examples_panel)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI.

    This function is separated so tests can import and exercise the
    parser without invoking side effects.
    """
    epilog = textwrap.dedent("""\
        Examples:
          routine-workflow                              # Run with defaults (dry-run enabled)
          routine-workflow -d                          # Explicit dry-run preview
          routine-workflow -nd -y                      # Real run, auto-confirm
          routine-workflow -s step2 step3 -w 4         # Selective steps, 4 workers
          routine-workflow -t 1800 -p /path/to/proj    # Timeout + custom root
          routine-workflow -es -eda                    # Enable security/audit gates (-es/-eda shortcuts)
          routine-workflow --fail-on-backup --yes      # Exit on backup fail, auto-confirm
          routine-workflow --create-dump-run-cmd create-dump batch run --dirs custom .""")

    parser = argparse.ArgumentParser(
        description='Production routine workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )

    parser.add_argument('-p', '--project-root', type=Path, default=Path(os.getenv('PROJECT_ROOT', os.getcwd())),
                        help='Project root path')
    parser.add_argument('-l', '--log-dir', type=Path, default=Path(os.getenv('LOG_DIR', '/sdcard/tools/logs')),
                        help='Directory to write logs')
    parser.add_argument('--log-file', type=Path, default=None, help='Optional single log file path')
    parser.add_argument('--lock-dir', type=Path, default=Path(os.getenv('LOCK_DIR', '/tmp/routine_workflow.lock')),
                        help='Lock directory used to guard a running workflow')
    parser.add_argument('--lock-ttl', type=int, default=int(os.getenv('LOCK_TTL', '3600')),
                        help='Lock eviction TTL in seconds (0=disable; default: 3600)')

    parser.add_argument('--clean-script', type=Path, default=Path(os.getenv('CLEAN_SCRIPT', '/sdcard/tools/clean.py')),
                        help='Cleanup script path')
    parser.add_argument('--backup-script', type=Path, default=Path(os.getenv('BACKUP_SCRIPT', '/sdcard/tools/create_backup.py')),
                        help='Backup script path')
    # env var name aligned with option name
    parser.add_argument('--create-dump-script', type=Path, default=Path(os.getenv('CREATE_DUMP_SCRIPT', '/sdcard/tools/run_create_dump.sh')),
                        help='Script used to create dumps')

    # Boolean flags (fail-on-backup and git-push)
    parser.add_argument('--fail-on-backup', action='store_true',
                        default=(os.getenv('FAIL_ON_BACKUP', '0') == '1'),
                        help='Exit if backup step fails')

    parser.add_argument('-y', '--yes', action='store_true', help='Auto-confirm prompts')

    # Dry-run defaults to enabled for safety; use -nd/--no-dry-run to perform real execution
    parser.add_argument('-d', '--dry-run', dest='dry_run', action='store_true', default=True,
                        help='Dry-run mode (default: enabled for safety)')
    parser.add_argument('-nd', '--no-dry-run', dest='dry_run', action='store_false',
                        help='Disable dry-run (perform real execution)')

    parser.add_argument('-w', '--workers', type=int, default=min(8, os.cpu_count() or 4),
                        help='Parallel workers for autoimport')
    parser.add_argument('-t', '--workflow-timeout', type=int, default=int(os.getenv('WORKFLOW_TIMEOUT', '0')),
                        help='Overall timeout in seconds (0=disable)')
    parser.add_argument('--exclude-patterns', nargs='*', default=None, help='Optional override exclude patterns')
    parser.add_argument('--create-dump-run-cmd', nargs=argparse.REMAINDER, default=None,
                        help='Override create-dump run command (base args before dynamic flags)')

    parser.add_argument(
        '-s', '--steps', nargs='+', default=None,
        help='Run specific steps only (space-separated, e.g., "step2 step3"). Supports custom order/repeats. Defaults to all.'
    )

    parser.add_argument('--test-cov-threshold', type=int, default=85,
                        help='Pytest coverage threshold (0=disable)')
    parser.add_argument('--git-push', action='store_true', help='Enable git commit/push in step 6 (default: false)')
    parser.add_argument('-es', '--enable-security', action='store_true',
                        help='Enable security scan in step 3.5 (default: false)')
    parser.add_argument('-eda', '--enable-dep-audit', action='store_true',
                        help='Enable dep audit in step 6.5 (default: false)')

    return parser


def validate_steps(steps: Optional[List[str]], available_steps: Set[str]) -> List[str]:
    """Validate and filter requested steps; warn and exit on fully-invalid sets.

    Returns a list of valid steps. If the incoming `steps` is falsy (None or empty)
    the function returns an empty list which the runner interprets as "run all steps".
    """
    if not steps:
        return []

    valid = [s for s in steps if s in available_steps]
    invalid = [s for s in steps if s not in available_steps]
    if invalid:
        print(f"Warning: Skipping invalid steps: {', '.join(invalid)}", file=sys.stderr)
        if not valid:
            # If the user specified steps but none are valid, bail out
            sys.exit(1)
    return valid


def main() -> int:
    parser = build_parser()

    # Early --help interception so rich can render a prettier help screen
    cli_args = sys.argv[1:]
    if len(cli_args) > 0 and cli_args[0] in ('-h', '--help'):
        if _has_rich():
            from rich.console import Console

            console = Console()
            render_rich_help(console, parser)
        else:
            parser.print_help()
        return 0

    # Normal parse
    args = parser.parse_args(cli_args)

    if args.dry_run:
        print("🛡️  Safety mode: Dry-run enabled (use -nd/--no-dry-run for real execution)")

    # Validate and normalize steps
    args.steps = validate_steps(args.steps, STEP_NAMES)

    cfg = WorkflowConfig.from_args(args)
    runner = WorkflowRunner(cfg, steps=args.steps)

    # Run and return integer exit code
    return runner.run()


if __name__ == '__main__':
    raise SystemExit(main())