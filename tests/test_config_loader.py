
import sys
import pytest
from unittest.mock import MagicMock, patch

# Try importing tomli/tomllib depending on python version
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from routine_workflow.config_loader import load_config

def test_load_config_no_pyproject(tmp_path):
    """Test load_config returns empty dict if pyproject.toml does not exist."""
    config = load_config(tmp_path)
    assert config == {}

def test_load_config_empty_pyproject(tmp_path):
    """Test load_config with an empty pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.touch()
    config = load_config(tmp_path)
    # empty file -> tomllib.load returns {}, get("tool", ...) defaults work
    assert config == {}

def test_load_config_invalid_toml(tmp_path):
    """Test load_config raises exception on invalid TOML."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("invalid_toml = [ unclosed list", encoding="utf-8")

    with pytest.raises(Exception): # tomllib.TOMLDecodeError or similar
        load_config(tmp_path)

def test_load_config_normalization(tmp_path):
    """Test that kebab-case keys are normalized to snake_case."""
    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.routine-workflow]
    some-setting = "value"
    another-setting-complex = 123
    normal_setting = true
    """
    pyproject.write_text(content, encoding="utf-8")

    config = load_config(tmp_path)
    assert config["some_setting"] == "value"
    assert config["another_setting_complex"] == 123
    assert config["normal_setting"] is True
    assert "some-setting" not in config
