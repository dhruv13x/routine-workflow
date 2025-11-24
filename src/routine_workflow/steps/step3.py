# src/routine_workflow/steps/step3.py


"""Step 3: Clean caches via external clean.py tool."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command


def clean_caches(runner: WorkflowRunner) -> None:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 3: Clean caches (via pypurge tool)')
    runner.logger.info('=' * 60)

    config = runner.config

    if not cmd_exists('pypurge'):
        runner.logger.warning('pypurge not found - skipping cleanup')
        return

    # Build flags dynamically
    # Usage: pypurge [root] --allow-root [options]
    cmd = ['pypurge', str(config.project_root)]
    cmd.append('--allow-root')  # Always for privileged access

    if config.dry_run:
        cmd.append('-p')  # Preview mode
    else:
        cmd.append('-y')  # Force non-interactive

    # Redundant auto_yes check not strictly needed if we trust dry_run, 
    # but good for consistency if user passes -y explicit to routine-workflow
    if config.auto_yes and '-y' not in cmd: 
        cmd.append('-y')

    description = 'Clean caches'

    success = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=300.0,
        fatal=False  # Advisory; continue on fail
    )

    if success["success"]:
        runner.logger.info('Cache cleanup completed successfully')
    else:
        runner.logger.warning('Cache cleanup failed or skipped')
