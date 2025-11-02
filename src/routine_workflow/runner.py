# routine_workflow/runner.py

"""Core workflow runner orchestration."""

from __future__ import annotations

import os
import signal
from typing import List, Tuple

from .config import WorkflowConfig
from .lock import lock_context, cleanup_and_exit
from .steps import (
    delete_old_dumps,
    reformat_code,
    clean_caches,
    backup_project,
    generate_dumps,
)
from .utils import setup_logging, setup_signal_handlers


class WorkflowRunner:
    def __init__(self, config: WorkflowConfig, steps: List[str] | None = None):
        self.config = config
        self.steps = steps
        self._lock_acquired = False
        self._pid_path = None
        self.logger = setup_logging(config)
        setup_signal_handlers(self)

    def run(self) -> int:
        # Install overall timeout via SIGALRM when supported and requested
        alarm_installed = False
        if self.config.workflow_timeout and hasattr(signal, "SIGALRM"):
            def _alarm_handler(signum, frame):
                self.logger.error(
                    f"Workflow timed out after {self.config.workflow_timeout} seconds"
                )
                cleanup_and_exit(self, 124)

            signal.signal(signal.SIGALRM, _alarm_handler)
            try:
                signal.alarm(int(self.config.workflow_timeout))
                alarm_installed = True
            except Exception as e:
                self.logger.warning(f"Could not set workflow timeout alarm: {e}")

        self.logger.info("=" * 60)
        self.logger.info("ROUTINE WORKFLOW START")
        self.logger.info(
            f"Root: {self.config.project_root} | Dry-run: {self.config.dry_run} | Workers: {self.config.max_workers}"
        )
        self.logger.info("=" * 60)

        os.chdir(self.config.project_root)

        with lock_context(self):
            try:
                all_steps: List[Tuple[str, callable]] = [
                    ("step1", delete_old_dumps),
                    ("step2", reformat_code),
                    ("step3", clean_caches),
                    ("step4", backup_project),
                    ("step5", generate_dumps),
                ]

                to_run = all_steps
                if self.steps:
                    step_map = {name: func for name, func in all_steps}
                    to_run = [
                        (name, step_map[name]) for name in self.steps if name in step_map
                    ]
                    skipped = {
                        name for name, _ in all_steps if name not in self.steps
                    }
                    if skipped:
                        self.logger.warning(f"Skipping steps: {', '.join(skipped)}")
                    if not to_run:
                        self.logger.warning("No valid steps specified; exiting early")
                        return 0

                backup_success = None
                for name, step_func in to_run:
                    self.logger.info(f"Executing {name}...")
                    if name == "step4":
                        backup_success = step_func(self)
                    else:
                        step_func(self)

                if backup_success is not None and not backup_success and self.config.fail_on_backup:
                    self.logger.error("Backup failed; aborting workflow per config")
                    return 2

                self.logger.info("WORKFLOW SUCCESS")
                return 0
            except SystemExit:
                raise
            except Exception as e:
                self.logger.exception(f"Workflow error: {e}")
                return 1
            finally:
                if alarm_installed:
                    try:
                        signal.alarm(0)
                    except Exception:
                        pass