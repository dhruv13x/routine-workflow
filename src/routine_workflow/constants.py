# src/routine_workflow/constants.py

"""Constants for the routine-workflow package."""

from typing import Dict, Set

# Maps all accepted aliases to their canonical step ID
STEP_ALIASES: Dict[str, str] = {
    "delete_dump": "step1",
    "delete_dumps": "step1",
    "reformat": "step2",
    "reformat_code": "step2",
    "pytest": "step2.5",
    "test": "step2.5",
    "tests": "step2.5",
    "clean_caches": "step3",
    "clean": "step3",
    "security": "step3.5",
    "scan": "step3.5",
    "backup": "step4",
    "create_dump": "step5",
    "dump": "step5",
    "dumps": "step5",
    "git": "step6",
    "commit": "step6",
    "audit": "step6.5",
    "dep_audit": "step6.5",
}

# For rich help text: maps canonical step ID to its primary alias
PRIMARY_ALIASES: Dict[str, str] = {
    "step1": "delete_dump",
    "step2": "reformat",
    "step2.5": "pytest",
    "step3": "clean",
    "step3.5": "security",
    "step4": "backup",
    "step5": "create_dump",
    "step6": "git",
    "step6.5": "audit",
}

# Canonical step names
STEP_NAMES: Set[str] = {
    "step1", "step2", "step2.5", "step3", "step3.5",
    "step4", "step5", "step6", "step6.5"
}
