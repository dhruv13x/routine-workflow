# src/routine_workflow/steps/step6.py

"""Step 6: Commit hygiene snapshot to git."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..utils import cmd_exists, run_command
from datetime import datetime


def commit_hygiene(runner: WorkflowRunner) -> bool:
    runner.logger.info('=' * 60)
    runner.logger.info('STEP 6: Commit hygiene snapshot to git')
    runner.logger.info('=' * 60)

    config = runner.config
    if config.dry_run or not config.git_push or not cmd_exists('git'):
        runner.logger.info('Git skipped (dry-run, disabled, or missing git)')
        return True

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f'routine_hygiene: {timestamp}'

    cmd_add = ['git', 'add', '.']
    cmd_commit = ['git', 'commit', '-m', commit_msg]
    cmd_push = ['git', 'push', '-u', 'origin', 'main']

    # Git add all changes
    if not run_command(runner, 'git add', cmd_add, fatal=True):
        return False

    # Commit if changes present
    commit_success = run_command(runner, 'git commit', cmd_commit, fatal=True)

    # Push (always, if commit succeeded or no changes)
    if commit_success or True:  # Push even on no-op commit for consistency
        if not run_command(runner, 'git push', cmd_push, fatal=True):
            return False

    if commit_success:
        runner.logger.info(f'Hygiene snapshot committed & pushed: {commit_msg}')
    else:
        runner.logger.info('No changes to commit; snapshot up-to-date')

    return True