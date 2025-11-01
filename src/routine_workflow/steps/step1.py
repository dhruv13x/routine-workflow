# routine_workflow/steps/step1.py

"""Step 1: Delete old code dumps via external code-dump tool."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command


def delete_old_dumps(runner: WorkflowRunner) -> None:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 1: Delete old code dumps (via code-dump tool)')
    runner.logger.info('=' * 60)

    config = runner.config

    if not cmd_exists('code-dump'):
        runner.logger.warning('code-dump not found - skipping cleanup')
        return

    # Build flags dynamically
    cmd = ['code-dump', 'batch', 'clean', str(config.project_root)]  # root as str arg
    if config.dry_run:
        cmd.append('-d')  # Tool-native dry preview
    else:
        cmd.append('-nd')  # Force real run
    if config.auto_yes:
        cmd.append('-y')  # Skip confirmations
    # Optional: Add -v for verbose if needed; defaults to true

    description = 'Clean old code dumps'

    success = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=60.0,
        fatal=False  # Advisory; continue on fail
    )

    if success:
        runner.logger.info('Code-dump cleanup completed successfully')
    else:
        runner.logger.warning('Code-dump cleanup failed or skipped')