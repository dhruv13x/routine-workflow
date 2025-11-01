# Routine Workflow

Production-grade automation for repository hygiene: code reformatting, cache cleaning, backups and dumps orchestration.

[PyPI Version](https://pypi.org/project/routine-workflow) • Tests Coverage

---

## Table of Contents

- Overview  
- Key Features  
- Installation  
- Quick Start  
- CLI Reference  
- Configuration  
- Workflow Steps  
- Logging & Locking  
- Testing & CI  
- Development  
- Troubleshooting  
- Contributing  
- License  

---

## Overview

`routine_workflow` is a small, robust Python package designed to automate routine repository maintenance tasks in production — including cleaning caches, running code formatting tools, creating backups, and producing code dumps via an external tool (formerly `code-dump`, now `create-dump`).  
It is written for reliability in CI and on developer machines and intended to be easy to integrate into cronjobs, CI pipelines, or run interactively.

This repository follows a `src/` layout and provides a CLI entrypoint, a dataclass-based configuration object, and a well-tested runner orchestration.

---

## Key Features

- Deterministic, configurable workflow orchestration  
- Safe locking to prevent concurrent runs  
- Dry-run mode for previewing operations  
- Pluggable external dump tool integration (`create-dump`)  
- Parallelizable tasks (autoimport / formatting) with configurable worker count  
- Thorough test coverage and CI-friendly behavior  

---

## Installation

Recommended: install inside a virtual environment.

```bash
# From PyPI (if published)
pip install routine-workflow

# From local source (editable)
git clone git@github.com:dhruv13x/routine-workflow.git
cd routine-workflow
python -m venv .venv
source .venv/bin/activate
pip install -e .


---

Quick Start

Run the workflow with defaults (uses sensible local defaults for logging, lock dir, and the create-dump helper script):

routine-workflow
# OR if running the package directly
python -m src.routine_workflow

Dry-run to preview actions without executing commands:

routine-workflow --dry-run

Run with increased verbosity (logs written to configured log_dir):

routine-workflow --project-root /path/to/project --log-dir /var/log/routine-workflow


---

CLI Reference

Run routine-workflow --help or refer to src/routine_workflow/cli.py for the most up-to-date options. Highlights:

--project-root PATH            Project root (default: $PROJECT_ROOT or current dir)
--log-dir PATH                 Directory for rotating logs (default: /sdcard/tools/logs)
--log-file PATH                Explicit log file path
--lock-dir PATH                Directory used for locking (default: /tmp/routine_workflow.lock)
--clean-script PATH            Path to clean helper script (default: /sdcard/tools/clean.py)
--backup-script PATH           Path to backup helper script (default: /sdcard/tools/create_backup.py)
--create-dump-script PATH      Path to external create-dump script (default: /sdcard/tools/run_create_dump.sh)
--create-dump-run-cmd ...      Override base run command for the create-dump tool
--fail-on-backup               Exit with error if backup fails
--yes                          Auto-confirm prompts
--dry-run                      Show actions without executing
--workers INT                  Parallel workers (default: min(8, CPU))
--workflow-timeout INT         Overall timeout in seconds (0 = disabled)
--exclude-patterns PATTERN ... File discovery exclude patterns


---

Configuration

Runtime configuration is encapsulated in WorkflowConfig (src/routine_workflow/config.py).
You can supply configuration via CLI flags or environment variables.

Defaults:

LOG_DIR: /sdcard/tools/logs

LOCK_DIR: /tmp/routine_workflow.lock

CREATE_DUMP_SCRIPT: /sdcard/tools/run_create_dump.sh

WORKFLOW_TIMEOUT: 0 (disabled)


Config exposes:

create_dump_script: Path
create_dump_clean_cmd: List[str]
create_dump_run_cmd: List[str]
fail_on_backup: bool
auto_yes: bool
dry_run: bool
max_workers: int
workflow_timeout: int
exclude_patterns: List[str]


---

Workflow Steps

The workflow orchestrates these steps (under src/routine_workflow/steps):

1. delete_old_dumps — prune old dumps


2. reformat_code — run autoformatter / autoimport helpers


3. clean_caches — remove temporary caches and artifacts


4. backup_project — create a backup of the project


5. generate_dumps — call create-dump tool to produce project dumps



Each step is idempotent and resilient to failures; fail_on_backup controls whether workflow aborts on backup failure.


---

Logging & Locking

Logging uses a RotatingFileHandler (5MB, 5 backups) plus console output.

Runner enforces directory-based lock (config.lock_dir) to prevent concurrent runs, validated by PID file contents.



---

Testing & CI

Run the tests locally:

pip install -r requirements-dev.txt
pytest -q

Example coverage:

81 passed
coverage: 96.73%

CI suggestions:

Run tests on every PR

Run linting (black, flake8)

Publish coverage reports



---

Development

Recommended workflow for contributors:

# create feature branch
git checkout -b feat/your-change

# run tests & fix
pytest -q

# commit and push; open PR
git commit -am "Describe change"
git push origin feat/your-change

Maintain a clean src/ layout and keep WorkflowConfig stable for backward compatibility.


---

Troubleshooting

Q: Why does it ask for credentials when pushing?
A: Use SSH remotes (git@github.com:...) or store a PAT for HTTPS remotes.

Q: .pyc or .coverage files appear after tests.
A: Add .gitignore with __pycache__/, *.pyc, .coverage, .bak.

Q: External create-dump tool not found.
A: Ensure create-dump is installed or specify --create-dump-script.


---

Contributing

Contributions welcome.

1. Open an issue for major changes


2. Fork the repo and submit PRs against main


3. Keep changes small, tested, and documented



Add a CONTRIBUTING.md for release/versioning and commit conventions.


---

Release & Versioning

Uses semantic versioning.
Tag releases with:

git tag -a v2.0.0 -m "Rename code-dump → create-dump (stable release)"
git push origin v2.0.0


---

License

MIT License — see LICENSE file.


---

Maintainers / Contact

dhruv13x — primary maintainer



---

Thank you for using routine_workflow.
Optional: I can generate CONTRIBUTING.md, CHANGELOG.md, and .github/workflows/ci.yml for CI automation.