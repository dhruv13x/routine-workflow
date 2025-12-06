
"""Custom exception classes for routine-workflow."""

from __future__ import annotations
from typing import Optional


class WorkflowError(Exception):
    """Base exception for all workflow-related errors."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion


class CommandNotFoundError(WorkflowError):
    """Raised when an external command/tool is missing."""

    def __init__(self, cmd: str, suggestion: Optional[str] = None):
        if not suggestion:
            suggestion = f"Please install '{cmd}' and ensure it is in your PATH."
        super().__init__(f"Command '{cmd}' not found", suggestion)
        self.cmd = cmd


class StepExecutionError(WorkflowError):
    """Raised when a step fails to execute correctly."""

    def __init__(self, step_name: str, reason: str, suggestion: Optional[str] = None):
        super().__init__(f"Step '{step_name}' failed: {reason}", suggestion)
        self.step_name = step_name
        self.reason = reason


class ConfigurationError(WorkflowError):
    """Raised when there is an issue with the configuration."""

    def __init__(self, detail: str, suggestion: Optional[str] = None):
        super().__init__(f"Configuration Error: {detail}", suggestion)


def format_error(error: Exception) -> str:
    """Format an exception into a user-friendly message with suggestions."""
    if isinstance(error, WorkflowError):
        msg = [f"❌ Error: {error.message}"]
        if error.suggestion:
            msg.append(f"💡 Suggestion: {error.suggestion}")
        return "\n".join(msg)

    return f"❌ Unexpected Error: {str(error)}"
