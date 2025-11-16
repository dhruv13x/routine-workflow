# src/routine_workflow/steps/step2.py

"""Step 2: Reformat code with tools."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command, run_autoimport_parallel


def reformat_code(runner: WorkflowRunner) -> None:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 2: Reformat + imports (ruff/autoflake/autoimport/isort)')
    runner.logger.info('=' * 60)

    config = runner.config
    if config.dry_run:
        runner.logger.info('DRY-RUN: Skipping reformat (tools lack native preview)')
        return

    if cmd_exists('ruff'):
        run_command(runner, 'Ruff initial format', ['ruff', 'format', '.'])

    if cmd_exists('autoflake'):
        run_command(runner, 'Autoflake cleanup', [
            'autoflake', '--recursive', '--in-place', '--remove-all-unused-imports',
            '--remove-unused-variables', '--ignore-init-module-imports', '.'
        ], timeout=600.0)

    if cmd_exists('autoimport'):
        run_autoimport_parallel(runner)
    else:
        runner.logger.info('autoimport not installed - skipping')

    if cmd_exists('isort'):
        run_command(runner, 'Isort sort', ['isort', '.', '--filter-files'])

    if cmd_exists('ruff'):
        run_command(runner, 'Ruff final check/fix', ['ruff', 'check', '.', '--fix'])
        run_command(runner, 'Ruff final format', ['ruff', 'format', '.'])

    runner.logger.info('Reformat complete')
