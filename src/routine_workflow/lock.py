# src/routine_workflow/lock.py


"""Locking mechanisms to prevent concurrent runs."""

from __future__ import annotations

import os
import shutil
import time  # New: for TTL checks
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
        ts_path = config.lock_dir / 'timestamp'  # New: Epoch timestamp
        ts_path.write_text(str(time.time()))
        runner._pid_path = pid_path  # Set for release validation
        runner._lock_acquired = True
        runner.logger.info(f"Lock acquired: {config.lock_dir} (PID {os.getpid()})")
    except FileExistsError:
        # New: TTL-based eviction attempt
        evicted = False
        if config.lock_ttl > 0:
            try:
                pid_path = config.lock_dir / 'pid'
                ts_path = config.lock_dir / 'timestamp'
                if ts_path.exists():
                    ts = float(ts_path.read_text())
                    if time.time() - ts > config.lock_ttl:
                        # Stale by TTL: evict
                        shutil.rmtree(config.lock_dir)
                        runner.logger.info(f"Evicted stale lock by TTL ({config.lock_ttl}s): {config.lock_dir}")
                        evicted = True
                    else:
                        # Fresh by TTL, but check PID liveness
                        if pid_path.exists():
                            pid_str = pid_path.read_text().strip()
                            try:
                                pid = int(pid_str)
                                os.kill(pid, 0)  # Raises OSError if dead
                            except (ValueError, OSError):
                                # Dead PID: evict
                                shutil.rmtree(config.lock_dir)
                                runner.logger.info(f"Evicted stale lock (dead PID): {config.lock_dir}")
                                evicted = True
                        else:
                            # No PID: treat as stale
                            shutil.rmtree(config.lock_dir)
                            runner.logger.info(f"Evicted stale lock (no PID): {config.lock_dir}")
                            evicted = True
                else:
                    # No timestamp: treat as stale
                    shutil.rmtree(config.lock_dir)
                    runner.logger.info(f"Evicted stale lock (no timestamp): {config.lock_dir}")
                    evicted = True
            except Exception as e:
                runner.logger.warning(f"Failed to evict stale lock: {e} — treating as active")
                evicted = False

        if not evicted:
            runner.logger.error(f"Lock exists: {config.lock_dir} — concurrent run detected")
            raise SystemExit(3)
        else:
            # Retry acquire after eviction
            config.lock_dir.mkdir(parents=True, exist_ok=False)
            pid_path = config.lock_dir / 'pid'
            pid_path.write_text(str(os.getpid()))
            ts_path = config.lock_dir / 'timestamp'
            ts_path.write_text(str(time.time()))
            runner._pid_path = pid_path
            runner._lock_acquired = True
            runner.logger.info(f"Lock acquired post-eviction: {config.lock_dir} (PID {os.getpid()})")
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
