from routine_workflow.errors import WorkflowError, CommandNotFoundError, format_error

def test_workflow_error_structure():
    """Test that WorkflowError holds message and suggestion."""
    error = WorkflowError("Something went wrong", suggestion="Try doing this instead")
    assert str(error) == "Something went wrong"
    assert error.suggestion == "Try doing this instead"

def test_command_not_found_error_defaults():
    """Test CommandNotFoundError has a default suggestion if not provided."""
    error = CommandNotFoundError("my-tool")
    assert "my-tool" in str(error)
    assert "install" in error.suggestion.lower()

def test_format_error_output():
    """Test that format_error produces the expected string output."""
    error = WorkflowError("Failed to connect", suggestion="Check your internet")
    output = format_error(error)
    assert "Failed to connect" in output
    assert "Suggestion" in output
    assert "Check your internet" in output
