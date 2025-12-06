
import pytest
from routine_workflow.errors import (
    WorkflowError,
    CommandNotFoundError,
    StepExecutionError,
    ConfigurationError,
    format_error
)

def test_workflow_error_structure():
    """Test that WorkflowError holds message and suggestion."""
    error = WorkflowError("Something went wrong", suggestion="Try doing this instead")
    assert str(error) == "Something went wrong"
    assert error.suggestion == "Try doing this instead"

def test_command_not_found_error_defaults():
    """Test CommandNotFoundError has a default suggestion if not provided."""
    error = CommandNotFoundError("my-tool")
    assert "Command 'my-tool' not found" in str(error)
    assert "install 'my-tool'" in error.suggestion

def test_command_not_found_error_custom_suggestion():
    """Test CommandNotFoundError with explicit suggestion."""
    error = CommandNotFoundError("my-tool", suggestion="Custom install instructions")
    assert "Command 'my-tool' not found" in str(error)
    assert error.suggestion == "Custom install instructions"

def test_step_execution_error():
    """Test StepExecutionError structure."""
    error = StepExecutionError("step1", "process exited with 1", suggestion="Check logs")
    assert "Step 'step1' failed: process exited with 1" in str(error)
    assert error.step_name == "step1"
    assert error.reason == "process exited with 1"
    assert error.suggestion == "Check logs"

def test_configuration_error():
    """Test ConfigurationError structure."""
    error = ConfigurationError("Invalid key", suggestion="Check config file")
    assert "Configuration Error: Invalid key" in str(error)
    assert error.suggestion == "Check config file"

def test_format_error_workflow_error():
    """Test format_error with WorkflowError."""
    error = WorkflowError("Failed to connect", suggestion="Check your internet")
    output = format_error(error)
    assert "❌ Error: Failed to connect" in output
    assert "💡 Suggestion: Check your internet" in output

def test_format_error_workflow_error_no_suggestion():
    """Test format_error with WorkflowError and no suggestion."""
    error = WorkflowError("Simple error")
    output = format_error(error)
    assert "❌ Error: Simple error" in output
    assert "Suggestion" not in output

def test_format_error_generic_exception():
    """Test format_error with generic Exception."""
    error = ValueError("Invalid value")
    output = format_error(error)
    assert "❌ Unexpected Error: Invalid value" in output
