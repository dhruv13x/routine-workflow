# src/routine_workflow/steps/step4.py

"""Step 4: Backup project via external backup script."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..backup_service import perform_backup


def backup_project(runner: WorkflowRunner) -> bool:
    """Delegate backup execution to the service layer."""
    return perform_backup(runner)
