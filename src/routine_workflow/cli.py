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
from typing import List, Optional, Set, Dict, Any

from .config import WorkflowConfig
from .config_loader import load_config
from .runner import WorkflowRunner
from .banner import print_logo
from .constants import STEP_NAMES, STEP_ALIASES, PRIMARY_ALIASES
from .prompt_service import run_interactive_mode
from .pre_commit_installer import install_pre_commit_hook


def _has_rich() -> bool:
    return importlib.util.find_spec("rich") is not None


def build_parser(defaults: Optional[Dict[str, Any]] = None) -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI.

    This function is separated so tests can import and exercise the
    parser without invoking side effects.

    Args:
        defaults: Optional dictionary of default values to override parser defaults.
    """
    from typing import Any  # Local import

    defaults = defaults or {}

    # Helper to get default value with precedence: supplied default -> parser default
    def get_default(key: str, fallback: Any) -> Any:
        return defaults.get(key, fallback)

    # --- UPDATED Epilog with new alias examples ---
    epilog = textwrap.dedent("""\
        Examples:
          routine-workflow                              # Run all steps (dry-run default)
          routine-workflow -nd -y                       # Real run, all steps
          routine-workflow -s reformat clean backup     # Run reformat, clean, and backup steps
          routine-workflow -s git -nd                   # Real run, only the 'git' step
          routine-workflow -s pytest audit              # Run tests and dependency audit
          routine-workflow -t 1800 -p /path/to/proj     # Timeout + custom root
          routine-workflow -es -eda                     # Enable security/audit gates
          routine-workflow --fail-on-backup --yes       # Exit on backup fail, auto-confirm
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

    # Logging args
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default=get_default('log_level', 'INFO'), help='Logging verbosity level')
    parser.add_argument('--log-format', type=str, choices=['text', 'json'],
                        default=get_default('log_format', 'text'), help='Log file format (text or json)')
    parser.add_argument('--log-rotation-max-bytes', type=int, default=get_default('log_rotation_max_bytes', 5*1024*1024),
                        help='Max bytes per log file before rotation')
    parser.add_argument('--log-rotation-backup-count', type=int, default=get_default('log_rotation_backup_count', 5),
                        help='Number of backup log files to keep')

    # Boolean flags need set_defaults if coming from config, because action='store_true' doesn't take 'default' well if we want to override it cleanly
    # Actually, argparse uses default=False for store_true. If we change the default to True via set_defaults, it works.

    parser.add_argument('--fail-on-backup', action='store_true',
                        help='Exit if backup step fails')

    parser.add_argument('-y', '--yes', action='store_true', help='Auto-confirm prompts')

    parser.add_argument('-d', '--dry-run', dest='dry_run', action='store_true',
                        help='Dry-run mode (default: enabled for safety)')
    parser.add_argument('-nd', '--no-dry-run', dest='dry_run', action='store_false',
                        help='Disable dry-run (perform real execution)')

    parser.add_argument('-w', '--workers', type=int, default=get_default('workers', min(8, os.cpu_count() or 4)),
                        help='Parallel workers for autoimport')
    parser.add_argument('-t', '--workflow-timeout', type=int, default=get_default('workflow_timeout', int(os.getenv('WORKFLOW_TIMEOUT', '0'))),
                        help='Overall timeout in seconds (0=disable)')
    parser.add_argument('--exclude-patterns', nargs='*', default=get_default('exclude_patterns', None), help='Optional override exclude patterns')
    parser.add_argument('--create-dump-run-cmd', nargs=argparse.REMAINDER, default=None,
                        help='Override create-dump run command (base args before dynamic flags)')

    parser.add_argument(
        '-s', '--steps', nargs='+', default=None,
        # --- UPDATED help text ---
        help='Run specific steps or aliases (e.g., "git backup pytest"). Supports custom order/repeats. Defaults to all.'
    )

    parser.add_argument('--test-cov-threshold', type=int, default=get_default('test_cov_threshold', 85),
                        help='Pytest coverage threshold (0=disable)')
    parser.add_argument('--git-push', action='store_true', help='Enable git commit/push in step 6 (default: false)')
    parser.add_argument('-es', '--enable-security', action='store_true',
                        help='Enable security scan in step 3.5 (default: false)')
    parser.add_argument('-eda', '--enable-dep-audit', action='store_true',
                        help='Enable dep audit in step 6.5 (default: false)')

    parser.add_argument('--profile', action='store_true',
                        help='Profile execution time of steps and workflow')

    parser.add_argument('--install-pre-commit', action='store_true',
                        help='Install routine-workflow as a pre-commit hook')

    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Enter interactive configuration mode')

    # Apply defaults for boolean flags if they exist in config
    # We do this by constructing a default map for parser.set_defaults, but since we are building parser here
    # we can just pass them to set_defaults at the end.

    # Calculate effective defaults
    bool_defaults = {
        'fail_on_backup': get_default('fail_on_backup', os.getenv('FAIL_ON_BACKUP', '0') == '1'),
        'dry_run': get_default('dry_run', True),
        'git_push': get_default('git_push', os.getenv('GIT_PUSH', '0') == '1'),
        'enable_security': get_default('enable_security', os.getenv('ENABLE_SECURITY', '0') == '1'),
        'enable_dep_audit': get_default('enable_dep_audit', os.getenv('ENABLE_DEP_AUDIT', '0') == '1'),
        'yes': get_default('auto_yes', False), # Map config 'auto_yes' to arg 'yes' if needed, or just 'yes'
    }
    # Note: config keys are normalized to snake_case.
    # 'yes' flag destination is 'yes'. Config might have 'auto_yes'?
    # Let's assume config uses 'yes' or we map it.
    # 'auto_yes' is in WorkflowConfig, but argparse dest is 'yes'.

    # If config has 'auto_yes', map it to 'yes'
    if 'auto_yes' in defaults:
        bool_defaults['yes'] = defaults['auto_yes']

    parser.set_defaults(**bool_defaults)
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s 9.0.2", help="Show program's version number and exit"
    )

    return parser


# --- UPDATED validate_steps function ---
def validate_steps(steps: Optional[List[str]], available_steps: Set[str], aliases: Dict[str, str]) -> List[str]:
    """Validate and translate requested steps/aliases; warn and exit on fully-invalid sets.

    Returns a list of valid, translated canonical step names.
    If the incoming `steps` is falsy (None or empty)
    the function returns an empty list which the runner interprets as "run all steps".
    """
    if not steps:
        return []
    
    translated_steps: List[str] = []
    invalid_steps: List[str] = []

    # --- REVISED LOGIC ---
    for step_name in steps:
        # 1. Check if it's a known alias (respects underscores)
        if step_name in aliases:
            translated_steps.append(aliases[step_name])
        # 2. Check if it's a canonical name (with underscore or dot)
        else:
            normalized_name = step_name.replace('_', '.')
            if normalized_name in available_steps:
                translated_steps.append(normalized_name)
            # 3. Otherwise, it's invalid
            else:
                invalid_steps.append(step_name) # Append the original name
    # --- END REVISED LOGIC ---

    if invalid_steps:
        print(f"Warning: Skipping invalid steps: {', '.join(invalid_steps)}", file=sys.stderr)
        if not translated_steps:
            # If the user specified steps but none are valid, bail out
            print(f"Error: No valid steps provided. Valid aliases are: {', '.join(sorted(aliases.keys()))}", file=sys.stderr)
            sys.exit(1)
    
    return translated_steps
# --- End UPDATED function ---


def main() -> int:
    # 1. First pass: Parse only project-root to locate config
    # We use a throwaway parser to find -p/--project-root without triggering required args errors (if any)
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('-p', '--project-root', type=Path, default=Path(os.getenv('PROJECT_ROOT', os.getcwd())))

    cli_args = sys.argv[1:]

    # Check for help early to avoid parsing partial args if help is requested
    # But we need to build the REAL parser to show help with correct defaults?
    # Actually, showing help with defaults from config is nice.
    # So we should try to load config even for help.

    known_args, _ = pre_parser.parse_known_args(cli_args)
    project_root = known_args.project_root.resolve()

    # 2. Load config from project root
    file_config = load_config(project_root)

    # 3. Build actual parser with loaded defaults
    parser = build_parser(defaults=file_config)

    # Early --help interception so rich can render a prettier help screen
    if len(cli_args) > 0 and cli_args[0] in ('-h', '--help'):
        if _has_rich():
            from rich.console import Console
            from .help_renderer import render_rich_help

            console = Console()
            render_rich_help(console, parser)
        else:
            parser.print_help()
        return 0

    print_logo()
    # Normal parse
    args = parser.parse_args(cli_args)

    if args.install_pre_commit:
        install_pre_commit_hook(project_root)
        return 0

    if args.interactive:
        args = run_interactive_mode(args)

    if args.dry_run:
        print("🛡️  Safety mode: Dry-run enabled (use -nd/--no-dry-run for real execution)")

    # --- UPDATED: Validate and translate steps using aliases ---
    args.steps = validate_steps(args.steps, STEP_NAMES, STEP_ALIASES)

    cfg = WorkflowConfig.from_args(args)
    runner = WorkflowRunner(cfg, steps=args.steps)

    # Run and return integer exit code
    return runner.run()


if __name__ == '__main__':
    raise SystemExit(main())