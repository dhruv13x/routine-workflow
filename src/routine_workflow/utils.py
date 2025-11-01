"""Utility functions for subprocess, file ops, and parallelism."""

from __future__ import annotations

import fnmatch
import logging
import os
import shlex
import shutil
import signal
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Sequence, Union

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runner import WorkflowRunner

from .config import WorkflowConfig
from .lock import cleanup_and_exit


def setup_logging(config: WorkflowConfig) -> logging.Logger:
    logger = logging.getLogger("routine_workflow")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        fmt = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        # Rotating file to avoid unbounded logs
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(config.log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
        fh.setFormatter(fmt)
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(ch)
        logger.propagate = False

    logger.info(f"Logging initialized → {config.log_file}")
    return logger


def setup_signal_handlers(runner: WorkflowRunner) -> None:
    def _handler(signum, frame):
        runner.logger.warning(f"Signal {signum} received — cleaning up")
        try:
            cleanup_and_exit(runner, 128 + int(signum))
        except SystemExit:
            raise
        except Exception:
            os._exit(1)

    # Only set common signals; SIGALRM is set conditionally in run()
    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def run_command(
    runner: WorkflowRunner,
    description: str,
    cmd: Union[Sequence[str], str],
    *,
    shell: bool = False,
    cwd: Optional[Path] = None,
    input_data: Optional[str] = None,
    timeout: float = 300.0,
    fatal: bool = False,
) -> bool:
    config = runner.config
    cwd_path = str(cwd) if cwd else str(config.project_root)

    # Normalize: prefer list; if cmd is string and not using shell, shlex.split it
    if isinstance(cmd, str):
        if shell:
            cmd_to_run = cmd  # pass string to subprocess when shell=True
        else:
            cmd_to_run = shlex.split(cmd)
    else:
        # cmd is a sequence
        if shell:
            cmd_to_run = ' '.join(shlex.quote(str(c)) for c in cmd)
        else:
            cmd_to_run = list(cmd)

    runner.logger.info(f">>> {description}: {cmd_to_run}")

    # Always execute for native dry-run outputs; steps append tool flags (-d/-nd)
    try:
        proc = subprocess.run(
            cmd_to_run,
            cwd=cwd_path,
            capture_output=True,
            text=True,
            shell=shell,
            input=input_data,
            timeout=timeout,
        )

        if proc.stdout:
            for line in proc.stdout.splitlines():
                runner.logger.info(f"  {line}")
        if proc.stderr:
            for line in proc.stderr.splitlines():
                runner.logger.warning(f"  {line}")

        success = proc.returncode == 0
        if success:
            runner.logger.info(f"✓ {description} (code {proc.returncode})")
        else:
            runner.logger.warning(f"✖ {description} (code {proc.returncode})")
            if fatal:
                runner.logger.error("Fatal command failure — aborting")
                cleanup_and_exit(runner, proc.returncode or 1)
        return success

    except subprocess.TimeoutExpired:
        runner.logger.error(f"Timeout ({timeout}s) while running: {description}")
        if fatal:
            cleanup_and_exit(runner, 124)
        return False
    except FileNotFoundError:
        runner.logger.error(f"Command not found for: {description}")
        if fatal:
            cleanup_and_exit(runner, 127)
        return False
    except Exception as e:
        runner.logger.exception(f"Unhandled exception running command: {description} — {e}")
        if fatal:
            cleanup_and_exit(runner, 1)
        return False


def cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def should_exclude(config: WorkflowConfig, file_path: Path) -> bool:
    try:
        rel_path = str(file_path.relative_to(config.project_root)).replace(os.sep, '/')
    except Exception:
        # if we can't relativize, treat as excluded
        return True
    for pat in config.exclude_patterns:
        if fnmatch.fnmatch(rel_path, pat):
            return True
        if pat.endswith('/*') and rel_path.startswith(pat[:-2] + '/'):
            return True
    return False


def gather_py_files(config: WorkflowConfig) -> List[Path]:
    files = [p for p in config.project_root.rglob('*.py') if not should_exclude(config, p)]
    files.sort()
    return files


def run_autoimport_parallel(runner: WorkflowRunner) -> None:
    config = runner.config
    py_files = gather_py_files(config)
    runner.logger.info(f"Processing {len(py_files)} files with {config.max_workers} workers")

    if not py_files:
        runner.logger.info("No files to process")
        return

    if config.dry_run:
        runner.logger.info(f"DRY-RUN: Would process {len(py_files)} files")
        return

    success_count = 0

    def _process(p: Path):
        ok = run_command(runner, f"Autoimport {p.name}", ["autoimport", "--keep-unused-imports", str(p)], cwd=p.parent, timeout=120.0)
        return (p, ok)

    with ThreadPoolExecutor(max_workers=config.max_workers) as ex:
        futures = {ex.submit(_process, p): p for p in py_files}
        for fut in as_completed(futures):
            try:
                _, ok = fut.result()
                if ok:
                    success_count += 1
            except Exception as e:
                runner.logger.warning(f"autoimport worker exception: {e}")

    runner.logger.info(f"Autoimport complete: {success_count}/{len(py_files)} successful")