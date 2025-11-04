# src/routine_workflow/steps/step6_5.py

"""Step 6.5: Dependency vulnerability audit post-git."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command


def dep_audit(runner: WorkflowRunner) -> bool:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 6.5: Dependency vulnerability audit')
    runner.logger.info('=' * 60)

    config = runner.config
    if config.dry_run or not config.enable_dep_audit:
        runner.logger.info('Dep audit skipped (dry-run or disabled)')
        return True

    if not cmd_exists('pip-audit'):
        runner.logger.warning('pip-audit not found - skipping dep audit')
        return True

    # Assume requirements.txt/pyproject.toml in root; extend as needed
    cmd = ['pip-audit', '--requirement', 'requirements.txt', '--format', 'json', '--ignore', 'vulnerability:low']  # Ignore low-severity

    description = 'pip-audit dep scan'
    success = run_command(
        runner, description, cmd,
        cwd=config.project_root,
        timeout=60.0,
        fatal=True  # Fail on high/medium vulns
    )

    if success:
        runner.logger.info('Dep audit passed - no vulnerable dependencies')
    else:
        runner.logger.error('Dep audit failed - vulns detected in requirements.txt; review before commit')
        return False  # Halt to prevent vulnerable snapshot commit

    return True