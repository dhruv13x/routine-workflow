"""Step 4: Backup project via external backup script."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command


def backup_project(runner: WorkflowRunner) -> bool:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 4: Backup project (via backup script)')
    runner.logger.info('=' * 60)

    config = runner.config
    if not config.backup_script.exists():
        runner.logger.info('Script missing - skip')
        return True

    if not cmd_exists('python3'):
        runner.logger.warning('python3 not found - skipping backup')
        return True

    # Build flags dynamically; note: short_note required—use timestamped default
    import datetime
    short_note = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_routine")
    cmd = [
        'python3', str(config.backup_script), short_note, '--archive'
    ]
    if config.dry_run:
        cmd.append('--dry-run')  # Tool-native preview
    if config.auto_yes:
        cmd.append('--yes')  # Skip confirmations

    description = 'Backup project'

    success = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=900.0,
        fatal=False  # Critical but continue with warn for advisory steps
    )

    if success:
        runner.logger.info('Backup completed successfully')
    else:
        runner.logger.warning('Backup failed or skipped')

    if not success and config.fail_on_backup:
        runner.logger.error('Backup failed + fail_on_backup - abort')
        return False
    return True