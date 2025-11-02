# routine_workflow/cli.py

"""CLI argument parsing and main entrypoint."""

import os
import sys
import argparse
from pathlib import Path

from .config import WorkflowConfig
from .runner import WorkflowRunner


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Production routine workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  %(prog)s                              # Run with defaults
  %(prog)s --dry-run                    # Preview actions
  %(prog)s --fail-on-backup --yes       # Exit on backup fail, auto-confirm
  %(prog)s --project-root /path/to/proj --workflow-timeout 1800
  %(prog)s --create-dump-run-cmd create-dump batch run --dirs custom .
''')

    parser.add_argument('--project-root', type=Path, default=Path(os.getenv('PROJECT_ROOT', os.getcwd())))
    parser.add_argument('--log-dir', type=Path, default=Path(os.getenv('LOG_DIR', '/sdcard/tools/logs')))
    parser.add_argument('--log-file', type=Path, default=None)
    parser.add_argument('--lock-dir', type=Path, default=Path(os.getenv('LOCK_DIR', '/tmp/routine_workflow.lock')))

    parser.add_argument('--clean-script', type=Path, default=Path(os.getenv('CLEAN_SCRIPT', '/sdcard/tools/clean.py')))
    parser.add_argument('--backup-script', type=Path, default=Path(os.getenv('BACKUP_SCRIPT', '/sdcard/tools/create_backup.py')))
    parser.add_argument('--create-dump-script', type=Path, default=Path(os.getenv('CODE_DUMP_SCRIPT', '/sdcard/tools/run_create_dump.sh')))  # Renamed for clarity; unused in binary mode

    parser.add_argument('--fail-on-backup', action='store_true', default=os.getenv('FAIL_ON_BACKUP', '0') == '1')
    parser.add_argument('--yes', action='store_true', help='Auto-confirm prompts')
    parser.add_argument('--dry-run', action='store_true', help='Show actions without executing')
    parser.add_argument('--workers', type=int, default=min(8, os.cpu_count() or 4), help='Parallel workers for autoimport')
    parser.add_argument('--workflow-timeout', type=int, default=int(os.getenv('WORKFLOW_TIMEOUT', '0')), help='Overall timeout in seconds (0 disable)')
    parser.add_argument('--exclude-patterns', nargs='*', default=None, help='Optional override exclude patterns')
    parser.add_argument('--create-dump-run-cmd', nargs=argparse.REMAINDER, default=None, help='Override create-dump run command (base args before dynamic flags)')
    parser.add_argument(
    '--steps', nargs='+', default=None,
    help='Run specific steps only (e.g., "step2" or "step2,step3"). Defaults to all.'
)

    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    cfg = WorkflowConfig.from_args(args)
    runner = WorkflowRunner(cfg, steps=args.steps)  # Pass to runner
    return runner.run()
