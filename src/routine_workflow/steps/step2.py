# src/routine_workflow/steps/step2.py

"""Step 2: Reformat code with tools."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runner import WorkflowRunner

from ..formatting_service import perform_reformat


def reformat_code(runner: WorkflowRunner) -> None:
    """Delegate reformat execution to the service layer."""
    perform_reformat(runner)
