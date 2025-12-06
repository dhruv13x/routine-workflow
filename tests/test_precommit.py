
import pytest
import sys
import yaml
from unittest.mock import patch, MagicMock
from pathlib import Path
from routine_workflow.cli import main
from routine_workflow.pre_commit_installer import install_pre_commit_hook

def test_install_pre_commit_creates_file(tmp_path):
    """Test that --install-pre-commit creates a .pre-commit-config.yaml file."""
    project_root = tmp_path
    config_file = project_root / ".pre-commit-config.yaml"

    install_pre_commit_hook(project_root)

    assert config_file.exists()
    with open(config_file) as f:
        content = yaml.safe_load(f)

    assert "repos" in content
    found = False
    for repo in content['repos']:
        if repo.get('repo') == 'local':
             for hook in repo.get('hooks', []):
                if hook.get('id') == 'routine-workflow':
                    found = True
                    break
    assert found

def test_install_pre_commit_updates_existing(tmp_path):
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

    install_pre_commit_hook(project_root)

    with open(config_file) as f:
        content = yaml.safe_load(f)

    # Check if old hook is still there
    assert any(h['id'] == 'trailing-whitespace' for r in content['repos'] for h in r['hooks'])
    # Check if new hook is added
    assert any(h['id'] == 'routine-workflow' for r in content['repos'] for h in r['hooks'])

def test_missing_pyyaml(tmp_path, capsys):
    """Test behavior when PyYAML is not installed."""
    with patch.dict(sys.modules, {'yaml': None}):
        with pytest.raises(SystemExit) as excinfo:
            install_pre_commit_hook(tmp_path)
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: PyYAML is required" in captured.err

def test_invalid_existing_config(tmp_path, capsys):
    """Test handling of invalid YAML in existing config."""
    config_file = tmp_path / ".pre-commit-config.yaml"
    config_file.write_text("INVALID YAML CONTENT : : :")

    with pytest.raises(SystemExit) as excinfo:
        install_pre_commit_hook(tmp_path)
    assert excinfo.value.code == 1

    captured = capsys.readouterr()
    assert "Error reading existing config" in captured.err

def test_empty_existing_config(tmp_path, capsys):
    """Test handling of empty existing config."""
    config_file = tmp_path / ".pre-commit-config.yaml"
    config_file.write_text("")

    install_pre_commit_hook(tmp_path)

    captured = capsys.readouterr()
    assert "Warning: Existing config was empty or invalid" in captured.out

    with open(config_file) as f:
        content = yaml.safe_load(f)
    assert "repos" in content

def test_read_permission_error(tmp_path, capsys):
    """Test handling of read permission errors."""
    config_file = tmp_path / ".pre-commit-config.yaml"
    config_file.touch()

    # We mock open to raise PermissionError when reading
    with patch("builtins.open", side_effect=[PermissionError("Permission denied"), MagicMock()]):
         with pytest.raises(SystemExit) as excinfo:
            install_pre_commit_hook(tmp_path)
         assert excinfo.value.code == 1
         captured = capsys.readouterr()
         assert "Error reading existing config" in captured.err

def test_write_error(tmp_path, capsys):
    """Test handling of write errors."""
    project_root = tmp_path

    # If exists is False, we only call open(..., 'w').
    with patch("builtins.open", side_effect=PermissionError("Write denied")):
        with pytest.raises(SystemExit) as excinfo:
            install_pre_commit_hook(project_root)
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error writing config" in captured.err

def test_hook_already_exists(tmp_path, capsys):
    """Test that hook is not duplicated if it already exists."""
    config_file = tmp_path / ".pre-commit-config.yaml"
    initial_content = {
        "repos": [
            {
                "repo": "local",
                "hooks": [{"id": "routine-workflow", "name": "routine-workflow"}]
            }
        ]
    }
    with open(config_file, "w") as f:
        yaml.dump(initial_content, f)

    install_pre_commit_hook(tmp_path)

    captured = capsys.readouterr()
    assert "Hook 'routine-workflow' already exists. Skipping." in captured.out

def test_local_repo_exists_but_no_hook(tmp_path, capsys):
    """Test adding hook to existing local repo block."""
    config_file = tmp_path / ".pre-commit-config.yaml"
    initial_content = {
        "repos": [
            {
                "repo": "local",
                "hooks": [{"id": "other-hook"}]
            }
        ]
    }
    with open(config_file, "w") as f:
        yaml.dump(initial_content, f)

    install_pre_commit_hook(tmp_path)

    captured = capsys.readouterr()
    assert "Added 'routine-workflow' hook to existing local repo block." in captured.out

    with open(config_file) as f:
        content = yaml.safe_load(f)

    local_repo = content['repos'][0]
    ids = [h['id'] for h in local_repo['hooks']]
    assert "routine-workflow" in ids
    assert "other-hook" in ids

def test_cli_integration(tmp_path):
    """Keep one test ensuring CLI calls the function."""
    project_root = tmp_path

    # cli.py main() returns integer exit code, doesn't raise SystemExit usually.
    # But if called via sys.exit(main()) in if __name__ == '__main__', it exits.
    # main() itself returns 0.

    with patch('sys.argv', ['routine-workflow', '--install-pre-commit', '-p', str(project_root)]):
        ret = main()
        assert ret == 0

    assert (project_root / ".pre-commit-config.yaml").exists()
