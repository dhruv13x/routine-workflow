import argparse
import sys
from typing import List, Set

from .constants import STEP_NAMES, STEP_ALIASES


def prompt_bool(question: str, default: bool = True) -> bool:
    """Prompt user for a yes/no question."""
    suffix = "[Y/n]" if default else "[y/N]"
    response = input(f"{question} {suffix} ").strip().lower()
    if not response:
        return default
    return response.startswith('y')


def prompt_steps() -> List[str] | None:
    """Prompt user to select steps."""
    print("\nAvailable steps:")
    for step in sorted(STEP_NAMES):
        print(f"  - {step}")
    print("\nAvailable aliases:")
    for alias, expansion in sorted(STEP_ALIASES.items()):
        print(f"  - {alias}: {expansion}")

    choice = input("\nSelect steps to run: [A]ll, or (C)ustom? [A] ").strip().upper()
    if not choice or choice == 'A':
        return None

    if choice == 'C':
        steps_input = input("Enter steps (space separated): ").strip()
        if not steps_input:
            print("No steps entered. Defaulting to all.")
            return None
        return steps_input.split()

    return None


def run_interactive_mode(args: argparse.Namespace) -> argparse.Namespace:
    """Run interactive configuration wizard."""
    print("\n🧩 Interactive Workflow Configuration 🧩\n")

    # 1. Select Steps
    selected_steps = prompt_steps()
    if selected_steps:
        args.steps = selected_steps
    else:
        args.steps = None # All steps

    # 2. Dry Run
    # Current args.dry_run comes from defaults.
    # We ask if they want to ENABLE real run if dry_run is True.
    # Or ask if they want dry run?
    # Better: "Enable real execution (disable dry-run)?"

    # If args.dry_run is True (default), we ask if they want to disable it.
    if prompt_bool("Enable real execution (disable dry-run)?", default=False):
        args.dry_run = False
    else:
        args.dry_run = True

    # 3. Fail on Backup
    if prompt_bool("Fail workflow if backup fails?", default=args.fail_on_backup):
        args.fail_on_backup = True
    else:
        args.fail_on_backup = False

    # 4. Git Push
    if prompt_bool("Push changes to git after execution?", default=args.git_push):
        args.git_push = True
    else:
        args.git_push = False

    # 5. Security Scan
    if prompt_bool("Enable Security Scan?", default=args.enable_security):
        args.enable_security = True
    else:
        args.enable_security = False

    # 6. Dep Audit
    if prompt_bool("Enable Dependency Audit?", default=args.enable_dep_audit):
        args.enable_dep_audit = True
    else:
        args.enable_dep_audit = False

    # Review
    print("\n📋 Configuration Review:")
    print(f"  Steps: {args.steps if args.steps else 'ALL'}")
    print(f"  Dry Run: {'✅ Yes' if args.dry_run else '❌ No (Real Execution)'}")
    print(f"  Fail on Backup: {args.fail_on_backup}")
    print(f"  Git Push: {args.git_push}")
    print(f"  Security Scan: {args.enable_security}")
    print(f"  Dep Audit: {args.enable_dep_audit}")

    if not prompt_bool("\nProceed with these settings?", default=True):
        print("Aborted by user.")
        sys.exit(0)

    return args
