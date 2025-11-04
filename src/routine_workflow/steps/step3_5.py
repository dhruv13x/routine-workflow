# src/routine_workflow/steps/step3_5.py

"""Step 3.5: Security vulnerability scan post-clean."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command


def security_scan(runner: WorkflowRunner) -> bool:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 3.5: Security vulnerability scan')
    runner.logger.info('=' * 60)

    config = runner.config
    if config.dry_run or not config.enable_security:
        runner.logger.info('Security scan skipped (dry-run or disabled)')
        return True

    tools = [
        ('bandit', ['bandit', '-r', '.', '-f', 'json', '--exclude', 'venv,__pycache__,node_modules', '--quiet']),
        ('safety', ['safety', 'check', '--full-report', '--json'])
    ]

    for tool_name, cmd in tools:
        if not cmd_exists(tool_name):
            runner.logger.warning(f'{tool_name} not found - skipping {tool_name} scan')
            continue

        description = f'{tool_name} security scan'
        success = run_command(
            runner, description, cmd,
            cwd=config.project_root,
            timeout=180.0,
            fatal=True  # Fail-fast on vulns
        )
        if not success:
            runner.logger.error(f'{tool_name} scan failed - aborting workflow')
            return False

    runner.logger.info('Security scans passed - no critical vulns found')
    return True