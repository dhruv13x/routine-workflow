
import pytest
import os
import yaml
from unittest.mock import patch, mock_open
from routine_workflow.cli import main

def test_install_pre_commit_creates_file(tmp_path, capsys):
    """Test that --install-pre-commit creates a .pre-commit-config.yaml file."""

    project_root = tmp_path
    config_file = project_root / ".pre-commit-config.yaml"

    with patch('sys.argv', ['routine-workflow', '--install-pre-commit', '-p', str(project_root)]):
        try:
            main()
        except SystemExit:
            pass

        assert config_file.exists()

        with open(config_file) as f:
            content = yaml.safe_load(f)

        assert "repos" in content
        found = False
        for repo in content['repos']:
            for hook in repo['hooks']:
                if hook.get('id') == 'routine-workflow':
                    found = True
                    break
        assert found

def test_install_pre_commit_updates_existing(tmp_path, capsys):
    """Test that it updates existing file without destroying other hooks."""
    project_root = tmp_path
    config_file = project_root / ".pre-commit-config.yaml"

    initial_content = {
        "repos": [
            {
                "repo": "https://github.com/pre-commit/pre-commit-hooks",
                "rev": "v4.0.0",
                "hooks": [{"id": "trailing-whitespace"}]
            }
        ]
    }

    with open(config_file, "w") as f:
        yaml.dump(initial_content, f)

    with patch('sys.argv', ['routine-workflow', '--install-pre-commit', '-p', str(project_root)]):
        try:
            main()
        except SystemExit:
            pass

        with open(config_file) as f:
            content = yaml.safe_load(f)

        # Check if old hook is still there
        assert any(h['id'] == 'trailing-whitespace' for r in content['repos'] for h in r['hooks'])
        # Check if new hook is added
        assert any(h['id'] == 'routine-workflow' for r in content['repos'] for h in r['hooks'])
