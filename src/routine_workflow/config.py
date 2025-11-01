# routine_workflow/config.py

"""Configuration dataclass for the workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from .defaults import default_exclude_patterns


def _default_clean_cmd() -> List[str]:
    return ['code-dump', 'batch', 'clean']


def _default_run_cmd() -> List[str]:
    return [
        'code-dump', 'batch', 'run',
        '--dirs', '., packages, packages/platform_core, packages/telethon_adapter_kit, services, services/forwarder_bot',  # Default; override via CLI
    ]


@dataclass(frozen=True)
class WorkflowConfig:
    project_root: Path
    log_dir: Path
    log_file: Path
    lock_dir: Path

    clean_script: Path
    backup_script: Path
    code_dump_script: Path  # Legacy; for bash fallback if needed

    # Code-dump cmds (base; dynamic flags appended in steps)
    code_dump_clean_cmd: List[str] = field(default_factory=_default_clean_cmd)
    code_dump_run_cmd: List[str] = field(default_factory=_default_run_cmd)

    fail_on_backup: bool = False
    auto_yes: bool = False
    dry_run: bool = False
    max_workers: int = field(default_factory=lambda: min(8, os.cpu_count() or 4))

    # overall workflow timeout in seconds (0 => disabled)
    workflow_timeout: int = 0

    exclude_patterns: List[str] = field(default_factory=default_exclude_patterns)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "WorkflowConfig":
        import argparse  # Lazy import for module isolation

        log_dir = args.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)

        if args.log_file:
            log_file = args.log_file
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"routine_{ts}.log"

        exclude_patterns = args.exclude_patterns if args.exclude_patterns else default_exclude_patterns()

        workers = args.workers if getattr(args, 'workers', None) is not None else min(8, os.cpu_count() or 4)

        # Handle CLI override for run cmd only
        code_dump_run_cmd = args.code_dump_run_cmd if args.code_dump_run_cmd else _default_run_cmd()
        code_dump_clean_cmd = _default_clean_cmd()  # No override; use default

        return cls(
            project_root=args.project_root.resolve(),
            log_dir=log_dir,
            log_file=log_file,
            lock_dir=args.lock_dir,
            clean_script=args.clean_script,
            backup_script=args.backup_script,
            code_dump_script=getattr(args, 'code_dump_script', Path('/sdcard/tools/run_code_dump.sh')),  # Fallback to env default
            code_dump_clean_cmd=code_dump_clean_cmd,
            code_dump_run_cmd=code_dump_run_cmd,
            fail_on_backup=args.fail_on_backup,
            auto_yes=args.yes,
            dry_run=args.dry_run,
            max_workers=workers,
            workflow_timeout=int(getattr(args, 'workflow_timeout', 0) or 0),
            exclude_patterns=exclude_patterns,
        )