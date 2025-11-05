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

    if not cmd_exists('git'):
        runner.logger.warning('git command not found, skipping step 6.')
        return True  # Not a failure, just a skip

    # Handle dry-run first by showing status
    if config.dry_run:
        runner.logger.info('DRY-RUN: Checking git status (no commit/push).')
        # Use stream=True for live output, fatal=False as it's just a preview
        run_command(
            runner,
            'Git status preview',
            ['git', 'status'],
            fatal=False,
            stream=True
        )
        return True

    # Handle if the feature is disabled (in a real run)
    if not config.git_push:
        runner.logger.info('Git push is disabled via config, skipping step 6.')
        return True

    # --- Real Run Logic ---
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f'routine_hygiene: {timestamp}'

    cmd_add = ['git', 'add', '.']
    cmd_commit = ['git', 'commit', '-m', commit_msg]
    cmd_push = ['git', 'push', '-u', 'origin', 'main']

    # Git add all changes
    # Note: run_command returns a dict, so we check ["success"]
    if not run_command(runner, 'git add', cmd_add, fatal=True)["success"]:
        return False

    # Commit if changes present
    # We set fatal=False here, as a failed commit (no changes) is not a fatal error.
    commit_result = run_command(runner, 'git commit', cmd_commit, fatal=False)
    commit_success = commit_result["success"]

    # Push only if the commit was successful
    if commit_success:
        if not run_command(runner, 'git push', cmd_push, fatal=True)["success"]:
            return False
        runner.logger.info(f'Hygiene snapshot committed & pushed: {commit_msg}')
    else:
        runner.logger.info('No changes to commit; snapshot up-to-date')

    return True
    