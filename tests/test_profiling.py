
import pytest
import sys
from unittest.mock import patch, MagicMock
from routine_workflow.cli import main
from routine_workflow.runner import WorkflowRunner

def test_profiling_output_captured(tmp_path, capsys):
    """Test that running with --profile produces a performance report."""

    # We pass -l (log-dir) to avoid trying to write to /sdcard

    with patch('sys.argv', ['routine-workflow', '--profile', '--dry-run', '-p', str(tmp_path), '-l', str(tmp_path / "logs")]), \
         patch('routine_workflow.runner.delete_old_dumps') as mock_s1, \
         patch('routine_workflow.runner.reformat_code') as mock_s2, \
         patch('routine_workflow.runner.clean_caches') as mock_s3, \
         patch('routine_workflow.runner.backup_project', return_value=True), \
         patch('routine_workflow.runner.generate_dumps'), \
         patch('routine_workflow.runner.run_tests'), \
         patch('routine_workflow.runner.security_scan'), \
         patch('routine_workflow.runner.commit_hygiene'), \
         patch('routine_workflow.runner.dep_audit'):

        # main() returns the exit code
        ret = main()
        assert ret == 0

        captured = capsys.readouterr()
        # Since we are modifying runner to print, these should appear.
        assert "Performance Report" in captured.out
        assert "Duration" in captured.out
