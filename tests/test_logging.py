
import logging
import os
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from routine_workflow.config import WorkflowConfig
from routine_workflow.utils import setup_logging

@pytest.fixture
def mock_config(tmp_path):
    return WorkflowConfig(
        project_root=tmp_path,
        log_dir=tmp_path / "logs",
        log_file=tmp_path / "logs/test.log",
        lock_dir=tmp_path / "lock",
        log_level="DEBUG",
        log_format="json",
        log_rotation_max_bytes=1024,
        log_rotation_backup_count=3,
        # Default mandatory fields
        dry_run=True,
    )

def test_setup_logging_configures_logger(mock_config):
    """Test that setup_logging configures the logger with new parameters."""
    with patch("routine_workflow.utils.RotatingFileHandler") as MockRotatingFileHandler:
        # Mock the handler instance to have a proper level attribute
        handler_instance = MagicMock()
        handler_instance.level = logging.NOTSET
        MockRotatingFileHandler.return_value = handler_instance

        logger = setup_logging(mock_config)

        # Verify logger level
        assert logger.level == logging.DEBUG

        # Verify RotatingFileHandler initialization
        MockRotatingFileHandler.assert_called_with(
            mock_config.log_file,
            maxBytes=1024,
            backupCount=3,
            encoding='utf-8'
        )

        # Verify formatter is set
        assert handler_instance.setFormatter.called

def test_json_formatting_integration(mock_config):
    """Test actual JSON formatting works."""
    # This test will actually write to a file
    mock_config.log_dir.mkdir(parents=True, exist_ok=True)

    # We need to ensure we don't mock RotatingFileHandler here, or we use a real one
    # The previous test mocked it, but patch is a context manager so it should be clean.
    # However, logger singleton persists. We should reset it.

    logger = logging.getLogger("routine_workflow")
    logger.handlers = [] # Clear handlers

    logger = setup_logging(mock_config)
    logger.info("Test message", extra={"foo": "bar"})

    # Read the log file
    log_content = mock_config.log_file.read_text()

    # Parse the last line as JSON
    last_line = log_content.strip().split('\n')[-1]
    log_data = json.loads(last_line)

    assert log_data['message'] == "Test message"
    assert log_data['level'] == "INFO"
    assert log_data['foo'] == "bar"

def test_text_formatting(mock_config):
    """Test standard text formatting."""
    mock_config.log_dir.mkdir(parents=True, exist_ok=True)

    # Override config to use text format
    # dataclasses are frozen, so we use replace or create new
    from dataclasses import replace
    text_config = replace(mock_config, log_format="text", log_file=mock_config.log_dir / "text.log")

    logger = logging.getLogger("routine_workflow")
    logger.handlers = [] # Clear handlers

    logger = setup_logging(text_config)
    logger.info("Text message")

    log_content = text_config.log_file.read_text()
    assert "INFO: Text message" in log_content
