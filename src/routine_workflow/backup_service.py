# src/routine_workflow/backup_service.py

"""Service layer for performing project backups."""

from __future__ import annotations
from typing import TYPE_CHECKING
import datetime

if TYPE_CHECKING:
    from .runner import WorkflowRunner

from .utils import cmd_exists, run_command


def perform_backup(runner: WorkflowRunner) -> bool:
    """Execute the project backup using projectclone."""
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 4: Backup project (via projectclone tool)')
    runner.logger.info('=' * 60)

    config = runner.config

    if not cmd_exists('projectclone'):
        runner.logger.warning('projectclone not found - skipping backup')
        return True

    # Build flags dynamically; note: short_note required—use timestamped default
    short_note = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_routine")

    # Usage: projectclone <short_note> --archive [options]
    cmd = [
        'projectclone', short_note, '--archive'
    ]

    if config.dry_run:
        cmd.append('--dry-run')
    else:
        cmd.append('--yes')  # Skip confirmation

    if config.auto_yes and '--yes' not in cmd:
        cmd.append('--yes')

    description = 'Backup project'

    success = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=900.0,
        fatal=False  # Critical but continue with warn for advisory steps
    )

    if success["success"]:
        runner.logger.info('Backup completed successfully')
    else:
        runner.logger.warning('Backup failed or skipped')

    if not success["success"] and config.fail_on_backup:
        runner.logger.error('Backup failed + fail_on_backup - abort')
        return False
    return True
