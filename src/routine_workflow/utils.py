# src/routine_workflow/utils.py

"""Utility functions for subprocess, file ops, and parallelism."""

from __future__ import annotations

import fnmatch
import importlib.util
import json
import logging
import os
import shlex
import shutil
import signal
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .runner import WorkflowRunner

from .config import WorkflowConfig
from .lock import cleanup_and_exit


def _has_rich() -> bool:
    """Check if rich is available (optional dep for enhanced logging)."""
    return importlib.util.find_spec("rich") is not None


class JSONFormatter(logging.Formatter):
    """Format logs as JSON objects."""

    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
            "path": record.pathname,
            "lineno": record.lineno,
        }

        # Include exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Include extra attributes
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename",
                               "funcName", "levelname", "levelno", "lineno", "module",
                               "msecs", "message", "msg", "name", "pathname", "process",
                               "processName", "relativeCreated", "stack_info", "thread", "threadName"]:
                     log_record[key] = value

        return json.dumps(log_record)


def setup_logging(config: WorkflowConfig) -> logging.Logger:
    logger = logging.getLogger("routine_workflow")

    # Set level from config
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    if logger.handlers:
        logger.warning("Logging handlers already exist; reusing existing setup")
    else:
        # File Handler
        fh = RotatingFileHandler(
            config.log_file,
            maxBytes=config.log_rotation_max_bytes,
            backupCount=config.log_rotation_backup_count,
            encoding='utf-8'
        )

        if config.log_format.lower() == "json":
            fh.setFormatter(JSONFormatter(datefmt='%Y-%m-%d %H:%M:%S'))
        else:
            fmt = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            fh.setFormatter(fmt)

        logger.addHandler(fh)

        # Console Handler
        if _has_rich():
            from rich.logging import RichHandler
            # RichHandler handles formatting beautifully by itself
            ch = RichHandler(
                show_level=True,
                show_path=False,
                omit_repeated_times=True
            )
            # We must set the level on the handler instance, not in the constructor
            # to remain compatible with tests that mock the constructor
            ch.setLevel(level)
        else:
            ch = logging.StreamHandler()
            fmt = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            ch.setFormatter(fmt)
            ch.setLevel(level)

        logger.addHandler(ch)
        logger.propagate = False

    logger.info(f"Logging initialized → {str(config.log_file)} (Rich: {_has_rich()}, Format: {config.log_format})")
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
    stream: bool = False,  # Live line logging for interactive tools (e.g., pytest)
) -> Dict[str, Union[bool, str]]:
    config = runner.config
    cwd_path = str(cwd) if cwd else str(config.project_root)

    # Normalize: prefer list; if cmd is string and not using shell, shlex.split it
    if isinstance(cmd, str):
        if shell:
            cmd_to_run = cmd
        else:
            cmd_to_run = shlex.split(cmd)
    else:
        if shell:
            cmd_to_run = ' '.join(shlex.quote(str(c)) for c in cmd)
        else:
            cmd_to_run = list(cmd)

    runner.logger.info(f">>> {description}: {cmd_to_run}")

    stdout = ""
    stderr = ""
    returncode = 0

    try:
        if stream:
            # Streaming mode: Popen for live line-by-line logging
            proc = subprocess.Popen(
                cmd_to_run,
                cwd=cwd_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data else None,
                text=True,
                shell=shell,
                bufsize=1,  # Line-buffered for streaming
                universal_newlines=True
            )

            def stream_pipe(pipe, log_func):
                try:
                    for line in iter(pipe.readline, ''):
                        if line:
                            log_func(line.rstrip())
                except subprocess.TimeoutExpired:
                    # swallow timeout — main thread handles it
                    pass
                except Exception as e:
                    # do not leak to stderr
                    runner.logger.debug(f"stream thread suppressed: {e}")

            # Daemon threads for non-blocking streaming
            stdout_thread = threading.Thread(target=stream_pipe, args=(proc.stdout, lambda l: runner.logger.info(f"[green]  {l}[/green]" if _has_rich() else f"  {l}")))
            stdout_thread.daemon = True
            stdout_thread.start()

            stderr_thread = threading.Thread(target=stream_pipe, args=(proc.stderr, lambda l: runner.logger.warning(f"[red]  {l}[/red]" if _has_rich() else f"  {l}")))
            stderr_thread.daemon = True
            stderr_thread.start()

            # Send input if needed and close stdin to signal EOF
            if input_data:
                proc.stdin.write(input_data)
                proc.stdin.close()

            # Wait for completion or timeout
            try:
                returncode = proc.wait(timeout=timeout)
                stdout, stderr = "", ""  # Streamed live; no capture needed
                
            except subprocess.TimeoutExpired:
                proc.kill()
                # Do not call proc.wait() again — test expects only one wait call
                returncode = 124
                stdout, stderr = "", ""
                
        else:
            # Original buffered mode
            proc = subprocess.run(
                cmd_to_run,
                cwd=cwd_path,
                capture_output=True,
                text=True,
                shell=shell,
                input=input_data,
                timeout=timeout,
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            returncode = proc.returncode

            # Log lines post-run for buffered mode
            for line in stdout.splitlines():
                if _has_rich():
                    runner.logger.info(f"[green]  {line}[/green]")
                else:
                    runner.logger.info(f"  {line}")
            for line in stderr.splitlines():
                if _has_rich():
                    runner.logger.warning(f"[red]  {line}[/red]")
                else:
                    runner.logger.warning(f"  {line}")

        success = returncode == 0
        if success:
            runner.logger.info(f"✓ {description} (code {returncode})")
        else:
            runner.logger.warning(f"✖ {description} (code {returncode})")
            if fatal:
                runner.logger.error("Fatal command failure — aborting")
                cleanup_and_exit(runner, returncode or 1)

        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr
        }

    except subprocess.TimeoutExpired as e:
        # Streaming mode: timeout already handled in wait block
        if stream:
            return {
                "success": False,
                "stdout": "",
                "stderr": ""
            }

        runner.logger.error(f"Timeout ({timeout}s) while running: {description}")
        if fatal:
            cleanup_and_exit(runner, 124)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"TimeoutExpired: {str(e)}"
        }

    except FileNotFoundError as e:
        runner.logger.error(f"Command not found for: {description}")
        if fatal:
            cleanup_and_exit(runner, 127)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"FileNotFoundError: {str(e)}"
        }
    except Exception as e:
        runner.logger.exception(f"Unhandled exception running command: {description} — {e}")
        if fatal:
            cleanup_and_exit(runner, 1)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Exception: {str(e)}"
        }


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

    if not cmd_exists('autoimport'):
        runner.logger.warning('autoimport not found - skipping')
        return

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
        result = run_command(runner, f"Autoimport {p.name}", ["autoimport", "--keep-unused-imports", str(p)], cwd=p.parent, timeout=120.0)
        ok = result["success"]
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
