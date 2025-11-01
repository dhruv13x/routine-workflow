# routine_workflow/lock.py

"""Locking mechanisms to prevent concurrent runs."""

from __future__ import annotations

import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runner import WorkflowRunner

from .config import WorkflowConfig


def acquire_lock(runner: WorkflowRunner) -> None:
    config = runner.config
    try:
        # Atomic mkdir for lock dir (fail if exists)
        config.lock_dir.mkdir(parents=True, exist_ok=False)
        pid_path = config.lock_dir / 'pid'
        pid_path.write_text(str(os.getpid()))
        runner._pid_path = pid_path  # Set for release validation
        runner._lock_acquired = True
        runner.logger.info(f"Lock acquired: {config.lock_dir} (PID {os.getpid()})")
    except FileExistsError:
        runner.logger.error(f"Lock exists: {config.lock_dir} — concurrent run detected")
        raise SystemExit(3)
    except Exception as e:
        runner.logger.exception(f"Failed to acquire lock: {e}")
        raise SystemExit(3)


def release_lock(runner: WorkflowRunner) -> None:
    if not runner._lock_acquired:
        return
    config = runner.config
    try:
        pid_path = runner._pid_path
        if pid_path and pid_path.exists():
            pid_text = pid_path.read_text().strip()
            if pid_text == str(os.getpid()):
                shutil.rmtree(config.lock_dir)
                runner.logger.info("Lock directory removed")
            else:
                runner.logger.warning("Lock owned by different PID — leaving it in place")
        else:
            # No PID file — best-effort stale removal
            if config.lock_dir.exists():
                shutil.rmtree(config.lock_dir)
                runner.logger.info("Stale lock dir removed")
    except Exception as e:
        runner.logger.warning(f"Error while releasing lock: {e}")
    finally:
        runner._lock_acquired = False
        runner._pid_path = None  # Reset for next run


@contextmanager
def lock_context(runner: WorkflowRunner):
    acquire_lock(runner)
    try:
        yield
    finally:
        release_lock(runner)


def cleanup_and_exit(runner: WorkflowRunner, exit_code: int = 0) -> None:
    # Best-effort release locks and exit
    try:
        release_lock(runner)
    finally:
        runner.logger.info(f"Exiting with code {exit_code}")
        raise SystemExit(exit_code)