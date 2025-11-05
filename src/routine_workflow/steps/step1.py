# routine_workflow/steps/step1.py

"""Step 1: Delete old code dumps via external create-dump tool."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command


def delete_old_dumps(runner: WorkflowRunner) -> None:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 1: Delete old code dumps (via create-dump tool)')
    runner.logger.info('=' * 60)

    config = runner.config

    if not cmd_exists('create-dump'):
        runner.logger.warning('create-dump not found - skipping cleanup')
        return

    # Build from config base; infer root via cwd (no positional path)
    cmd = config.create_dump_clean_cmd[:]
    if config.dry_run:
        cmd.append('-d')  # Tool-native dry preview
    else:
        cmd.append('-nd')  # Force real run
        cmd.append('-y')  # Force non-interactive for destructive clean

    description = 'Clean old code dumps'

    success = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=300.0,  # Aligned with step3/5; ample for large archives
        fatal=False  # Advisory; continue on fail
    )

    if success["success"]:
        runner.logger.info('Code-dump cleanup completed successfully')
    else:
        runner.logger.warning('Code-dump cleanup failed or skipped')