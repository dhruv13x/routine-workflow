# routine_workflow/steps/step3.py

"""Step 3: Clean caches via external clean.py tool."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command


def clean_caches(runner: WorkflowRunner) -> None:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 3: Clean caches (via clean.py tool)')
    runner.logger.info('=' * 60)

    config = runner.config
    if not config.clean_script.exists():
        runner.logger.info('Script missing - skip')
        return

    # Build flags dynamically
    cmd = ['python3', str(config.clean_script), str(config.project_root)]  # root as first arg (per parser)
    cmd.append('--allow-root')  # Always for privileged access
    if config.dry_run:
        cmd.append('--preview')  # Tool-native dry mode
    if config.auto_yes:
        cmd.append('-y')  # Skip confirmations

    description = 'Clean caches'

    success = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=300.0,
        fatal=False  # Advisory; continue on fail
    )

    if success:
        runner.logger.info('Cache cleanup completed successfully')
    else:
        runner.logger.warning('Cache cleanup failed or skipped')