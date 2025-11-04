# routine_workflow/steps/__init__.py

"""Workflow step implementations."""

from .step1 import delete_old_dumps
from .step2 import reformat_code
from .step2_5 import run_tests  # New: post-reformat validation
from .step3 import clean_caches
from .step3_5 import security_scan  # New: post-clean vuln scan
from .step4 import backup_project
from .step5 import generate_dumps
from .step6 import commit_hygiene  # New: post-dump git snapshot
from .step6_5 import dep_audit  # New: post-git dep audit

__all__ = [
    "delete_old_dumps",
    "reformat_code",
    "run_tests",
    "clean_caches",
    "security_scan",
    "backup_project",
    "generate_dumps",
    "commit_hygiene",
    "dep_audit",
]