import argparse
import sys
import pytest
from unittest.mock import patch
from routine_workflow.prompt_service import run_interactive_mode, prompt_steps

def test_interactive_mode_all_steps_real_run():
    args = argparse.Namespace()
    args.steps = None
    args.dry_run = True
    args.yes = False
    args.fail_on_backup = False
    args.git_push = False
    args.enable_security = False
    args.enable_dep_audit = False

    # Inputs:
    # 1. Select steps: "A"
    # 2. Enable real run: "y" -> args.dry_run = False
    # 3. Fail backup: "" (default False) -> args.fail_on_backup = False
    # 4. Git Push: "" (default False) -> args.git_push = False
    # 5. Security: "" (default False)
    # 6. Dep Audit: "" (default False)
    # 7. Proceed: "y"
    inputs = ["A", "y", "", "", "", "", "y"]

    with patch("builtins.input", side_effect=inputs):
        updated_args = run_interactive_mode(args)

    assert updated_args.dry_run is False
    assert updated_args.steps is None
    assert updated_args.fail_on_backup is False
    assert updated_args.git_push is False

def test_interactive_mode_custom_steps():
    args = argparse.Namespace()
    args.steps = None
    args.dry_run = True
    args.yes = False
    args.fail_on_backup = True
    args.git_push = False
    args.enable_security = False
    args.enable_dep_audit = False

    # Inputs:
    # 1. Select steps: "C"
    # 2. Steps: "git backup"
    # 3. Enable real run: "n" -> dry_run True
    # 4. Fail backup: "y" -> fail_on_backup True
    # 5. Git Push: "y" -> git_push True
    # 6. Security: "y" -> enable_security True
    # 7. Dep Audit: "y" -> enable_dep_audit True
    # 8. Proceed: "y"
    inputs = ["C", "git backup", "n", "y", "y", "y", "y", "y"]

    with patch("builtins.input", side_effect=inputs):
        updated_args = run_interactive_mode(args)

    assert updated_args.steps == ["git", "backup"]
    assert updated_args.dry_run is True
    assert updated_args.fail_on_backup is True
    assert updated_args.git_push is True
    assert updated_args.enable_security is True
    assert updated_args.enable_dep_audit is True

def test_interactive_mode_custom_steps_empty_input():
    # Test entering empty string for custom steps defaults to All
    args = argparse.Namespace()
    args.steps = None
    args.dry_run = True
    args.yes = False
    args.fail_on_backup = False
    args.git_push = False
    args.enable_security = False
    args.enable_dep_audit = False

    # Inputs:
    # 1. Select steps: "C"
    # 2. Steps: "" (empty) -> Should print default to all and return None
    # 3. Real run: "" (default False)
    # 4. Fail backup: ""
    # 5. Git push: ""
    # 6. Security: ""
    # 7. Dep audit: ""
    # 8. Proceed: "y"
    inputs = ["C", "", "", "", "", "", "", "y"]

    with patch("builtins.input", side_effect=inputs):
        updated_args = run_interactive_mode(args)

    assert updated_args.steps is None

def test_interactive_mode_abort():
    args = argparse.Namespace()
    args.steps = None
    args.dry_run = True
    args.yes = False
    args.fail_on_backup = False
    args.git_push = False
    args.enable_security = False
    args.enable_dep_audit = False

    # Inputs:
    # 1. Select steps: "A"
    # 2. Real run: ""
    # 3. Fail backup: ""
    # 4. Git push: ""
    # 5. Security: ""
    # 6. Dep audit: ""
    # 7. Proceed: "n" -> Should exit
    inputs = ["A", "", "", "", "", "", "n"]

    with patch("builtins.input", side_effect=inputs), pytest.raises(SystemExit):
        run_interactive_mode(args)

def test_interactive_mode_explicit_no_for_bools():
    # Cover 'else' branches for booleans
    args = argparse.Namespace()
    args.steps = None
    args.dry_run = True
    args.yes = False
    args.fail_on_backup = True
    args.git_push = True
    args.enable_security = True
    args.enable_dep_audit = True

    # Inputs:
    # 1. Select steps: "A"
    # 2. Real run: "n" -> dry_run True (else branch of first prompt)
    # 3. Fail backup: "n" -> fail_on_backup False
    # 4. Git push: "n" -> git_push False
    # 5. Security: "n" -> enable_security False
    # 6. Dep audit: "n" -> enable_dep_audit False
    # 7. Proceed: "y"
    inputs = ["A", "n", "n", "n", "n", "n", "y"]

    with patch("builtins.input", side_effect=inputs):
        updated_args = run_interactive_mode(args)

    assert updated_args.dry_run is True
    assert updated_args.fail_on_backup is False
    assert updated_args.git_push is False
    assert updated_args.enable_security is False
    assert updated_args.enable_dep_audit is False
