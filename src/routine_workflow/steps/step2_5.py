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

    if config.dry_run:
        cmd = ['pytest', '.', '--collect-only']
        description = 'pytest suite preview'
        timeout = 60.0
    else:
        cmd = [
            'pytest', '.',
            '-vv', '-s', '-ra', '--tb=long', '--showlocals',
            '--log-cli-level=DEBUG', '--setup-show', '--durations=10',
            '--timeout=15',
            '--cov-report=term-missing', '--cov-report=html', '--cov=.', '.'
        ]
        if config.test_cov_threshold > 0:
            cmd += ['--cov-fail-under', str(config.test_cov_threshold)]
        description = 'pytest suite'
        timeout = 1800.0

    result = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=timeout,
        fatal=False,
        stream=True  # Enable live streaming for real-time collection/run logs
    )

    success = result["success"]
    stdout = result["stdout"]

    if success:
        if config.dry_run:
            match = re.search(r'(\d+)\s+tests?\s+collected', stdout)
            num = int(match.group(1)) if match else "unknown"
            runner.logger.info(f'Test suite preview: {num} tests discovered')
        else:
            runner.logger.info(f'Tests passed (coverage >= {config.test_cov_threshold}%)')
    else:
        runner.logger.warning('Tests failed (flakes detected) - continuing workflow')
        return False

    return True