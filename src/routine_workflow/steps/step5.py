"""Step 5: Generate code dumps via external code-dump tool."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command


def generate_dumps(runner: WorkflowRunner) -> None:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 5: Generate code dumps (via code-dump tool)')
    runner.logger.info('=' * 60)

    config = runner.config

    if not cmd_exists('code-dump'):
        runner.logger.warning('code-dump not found - skipping generation')
        return

    # Assume config.code_dump_run_cmd is base like ['code-dump', 'batch', 'run', '--dirs', '.,packages,services']
    # Override/extend with dynamic flags; fallback if not set
    cmd = config.code_dump_run_cmd or ['code-dump', 'batch', 'run', '--dirs', '., packages, packages/platform_core, packages/telethon_adapter_kit, services, services/forwarder_bot']
    if not config.dry_run:
        cmd.append('-nd')  # Force real run (default is dry for 'run' subcommand)
    if config.auto_yes:
        cmd.append('-y')  # Skip prompts (confirmation on -nd)

    description = 'Batch generate code dumps'

    success = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=600.0,  # Ample for multi-dir
        fatal=False  # Advisory
    )

    if success:
        runner.logger.info('Code-dump generation completed successfully')
    else:
        runner.logger.warning('Code-dump generation failed or skipped')