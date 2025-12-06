# src/routine_workflow/config.py


"""Configuration dataclass for the workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from .defaults import default_exclude_patterns


def _default_clean_cmd() -> List[str]:
    return ['create-dump', 'batch', 'clean']


def _default_run_cmd() -> List[str]:
    return [
        'create-dump', 'batch', 'run',
        '--dirs', '., packages, packages/platform_core, packages/telethon_adapter_kit, services, services/forwarder_bot',  # Default; override via CLI
    ]


@dataclass(frozen=True)
class WorkflowConfig:
    # Positional (non-default) fields first
    project_root: Path
    log_dir: Path
    log_file: Path
    lock_dir: Path

    # Defaults follow
    lock_ttl: int = 3600
    create_dump_clean_cmd: List[str] = field(default_factory=_default_clean_cmd)
    create_dump_run_cmd: List[str] = field(default_factory=_default_run_cmd)

    fail_on_backup: bool = False
    auto_yes: bool = False
    dry_run: bool = field(default=True)
    max_workers: int = field(default_factory=lambda: min(8, os.cpu_count() or 4))
    test_cov_threshold: int = 85
    git_push: bool = False
    enable_security: bool = False
    enable_dep_audit: bool = False
    profile: bool = False

    # logging
    log_level: str = "INFO"
    log_format: str = "text"
    log_rotation_max_bytes: int = 5 * 1024 * 1024
    log_rotation_backup_count: int = 5

    # overall workflow timeout in seconds (0 => disabled)
    workflow_timeout: int = 0

    exclude_patterns: List[str] = field(default_factory=default_exclude_patterns)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "WorkflowConfig":
        import argparse  # Lazy import for module isolation

        log_dir = args.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)

        # Generate log_file if not provided
        if args.log_file is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"routine_{ts}.log"
        else:
            log_file = args.log_file

        exclude_patterns = args.exclude_patterns if args.exclude_patterns else default_exclude_patterns()

        workers = args.workers if hasattr(args, 'workers') and args.workers is not None else min(8, os.cpu_count() or 4)

        # Handle CLI override for run cmd only
        create_dump_run_cmd = args.create_dump_run_cmd if args.create_dump_run_cmd else _default_run_cmd()
        create_dump_clean_cmd = _default_clean_cmd()  # No override; use default

        # Env fallbacks for new flags
        enable_security = os.getenv('ENABLE_SECURITY', '0') == '1' or args.enable_security
        enable_dep_audit = os.getenv('ENABLE_DEP_AUDIT', '0') == '1' or args.enable_dep_audit
        test_cov_threshold = args.test_cov_threshold if hasattr(args, 'test_cov_threshold') else 85
        git_push = os.getenv('GIT_PUSH', '0') == '1' or args.git_push
        lock_ttl = args.lock_ttl if hasattr(args, 'lock_ttl') else int(os.getenv('LOCK_TTL', '3600'))

        profile = getattr(args, 'profile', False)

        # Logging from args or env
        log_level = getattr(args, 'log_level', os.getenv('LOG_LEVEL', 'INFO'))
        log_format = getattr(args, 'log_format', os.getenv('LOG_FORMAT', 'text'))
        log_rotation_max_bytes = getattr(args, 'log_rotation_max_bytes', int(os.getenv('LOG_ROTATION_MAX_BYTES', str(5*1024*1024))))
        log_rotation_backup_count = getattr(args, 'log_rotation_backup_count', int(os.getenv('LOG_ROTATION_BACKUP_COUNT', '5')))

        return cls(
            project_root=args.project_root.resolve(),
            log_dir=log_dir,
            log_file=log_file,
            lock_dir=args.lock_dir,
            lock_ttl=lock_ttl,
            create_dump_clean_cmd=create_dump_clean_cmd,
            create_dump_run_cmd=create_dump_run_cmd,
            fail_on_backup=args.fail_on_backup,
            auto_yes=args.yes,
            dry_run=args.dry_run,
            max_workers=workers,
            workflow_timeout=args.workflow_timeout or 0,
            exclude_patterns=exclude_patterns,
            test_cov_threshold=test_cov_threshold,
            git_push=git_push,
            enable_security=enable_security,
            enable_dep_audit=enable_dep_audit,
            profile=profile,
            log_level=log_level,
            log_format=log_format,
            log_rotation_max_bytes=log_rotation_max_bytes,
            log_rotation_backup_count=log_rotation_backup_count,
        )
