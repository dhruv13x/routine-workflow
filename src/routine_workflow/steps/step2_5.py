# src/routine_workflow/steps/step2_5.py

"""Step 2.5: Run pytest suite post-reformat."""

from __future__ import annotations
from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command


def run_tests(runner: WorkflowRunner) -> bool:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 2.5: Run pytest suite')
    runner.logger.info('=' * 60)

    config = runner.config
    if not cmd_exists('pytest'):
        runner.logger.warning('pytest not found - skipping tests')
        return True

    cmd = ['pytest', '.', '--cov=src', '--cov-report=term-missing', '-q']
    if config.test_cov_threshold > 0:
        cmd += ['--cov-fail-under', str(config.test_cov_threshold)]
    if config.dry_run:
        cmd += ['--collect-only']  # Preview without execution
    if not config.dry_run and config.max_workers > 1:  # Parallel only for real runs
        cmd += ['-n', str(config.max_workers)]

    description = 'pytest suite'

    result = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=300.0,
        fatal=True  # Fail-fast on test failures
    )

    success = result["success"]
    stdout = result["stdout"]

    if success:
        if config.dry_run:
            # Parse collection count from stdout (e.g., "1682 tests collected")
            match = re.search(r'(\d+)\s+tests?\s+collected', stdout)
            num_collected = int(match.group(1)) if match else "unknown"
            runner.logger.info(f'Test suite preview: {num_collected} tests discovered')
        else:
            runner.logger.info('Tests passed (coverage >= {}%)'.format(config.test_cov_threshold))
    else:
        runner.logger.error('Tests failed - aborting workflow')
        return False

    return True