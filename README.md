<div align="center">
  <img src="https://raw.githubusercontent.com/dhruv13x/routine-workflow/main/routine-workflow_logo.png" alt="routine-workflow logo" width="200"/>
</div>

<div align="center">

<!-- Package Info -->
[![PyPI version](https://img.shields.io/pypi/v/routine-workflow.svg)](https://pypi.org/project/routine-workflow/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
![Wheel](https://img.shields.io/pypi/wheel/routine-workflow.svg)
[![Release](https://img.shields.io/badge/release-PyPI-blue)](https://pypi.org/project/routine-workflow/)

<!-- Build & Quality -->
[![Build status](https://github.com/dhruv13x/routine-workflow/actions/workflows/publish.yml/badge.svg)](https://github.com/dhruv13x/routine-workflow/actions/workflows/publish.yml)
[![Codecov](https://codecov.io/gh/dhruv13x/routine-workflow/graph/badge.svg)](https://codecov.io/gh/dhruv13x/routine-workflow)
[![Test Coverage](https://img.shields.io/badge/coverage-90%25%2B-brightgreen.svg)](https://github.com/dhruv13x/routine-workflow/actions/workflows/test.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linting-ruff-yellow.svg)](https://github.com/astral-sh/ruff)
![Security](https://img.shields.io/badge/security-CodeQL-blue.svg)

<!-- Usage -->
![Downloads](https://img.shields.io/pypi/dm/routine-workflow.svg)
![OS](https://img.shields.io/badge/os-Linux%20%7C%20macOS%20%7C%20Windows-blue.svg)
[![Python Versions](https://img.shields.io/pypi/pyversions/routine-workflow.svg)](https://pypi.org/project/routine-workflow/)

<!-- License -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- Docs -->
[![Docs](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://your-docs-link)

</div>

# Routine Workflow

Production-grade automation for repository hygiene: code reformatting, cache cleaning, backups and dumps orchestration and much more.

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

## ✨ Key Features

- **🛡️ Safe by Default**: Ships with dry-run enabled to prevent accidental changes.
- **⚙️ Extensible Step Runner**: Run steps in any order, repeat them, or run a custom selection.
- **🧩 Alias-Driven**: Use intuitive aliases like `reformat`, `clean`, or `pytest`.
- **⚡ Parallel Execution**: Runs formatting and other tasks in parallel to save time.
- **✅ Integrated Testing**: Run your `pytest` suite as part of the workflow.
- **🔒 Concurrency Safe**: A robust file-based lock prevents multiple instances from running simultaneously.
- **🔍 Security & Auditing**: Built-in steps for security scanning and dependency auditing.
- **✍️ Git Integration**: Automatically commit and push a hygiene snapshot after a successful run.

---

## Installation

### Prerequisites

- Python 3.9+
- `pip` for package installation

### From PyPI

```bash
pip install routine-workflow
```

> **Note**
> For an enhanced `--help` experience with rich formatting, install `rich`:
> `pip install "routine-workflow[rich]"`

### From Source (for development)

```bash
git clone https://github.com/dhruv13x/routine-workflow.git
cd routine-workflow
pip install -e .[dev]
```

---

## 🚀 Quick Start

Run all default steps in dry-run mode (the safest default).

```bash
routine-workflow
```

To execute the workflow, disable dry-run mode:

```bash
routine-workflow -nd -y
```

Run only specific steps using their aliases:

```bash
routine-workflow -s reformat clean backup -nd
```

Run the integrated test suite and dependency audit:

```bash
routine-workflow -s pytest audit -nd
```


---

## ⚙️ Configuration & Advanced Usage

### CLI Arguments

This table provides a comprehensive list of all CLI arguments.

| Flag(s) | Description | Default |
|---|---|---|
| `-p`, `--project-root` | Project root path. | CWD |
| `-l`, `--log-dir` | Directory to write logs. | `/sdcard/tools/logs` |
| `--log-file` | Optional single log file path. | `None` |
| `--lock-dir` | Lock directory to prevent concurrent runs. | `/tmp/routine_workflow.lock` |
| `--lock-ttl` | Lock eviction TTL in seconds (0=disable). | `3600` |
| `--fail-on-backup` | Exit if backup step fails. | `False` |
| `-y`, `--yes` | Auto-confirm prompts. | `False` |
| `-d`, `--dry-run` | Dry-run mode (default for safety). | `True` |
| `-nd`, `--no-dry-run` | Disable dry-run (perform real execution). | `False` |
| `-w`, `--workers` | Parallel workers for supported tasks. | `min(8, CPU)` |
| `-t`, `--workflow-timeout` | Overall timeout in seconds (0=disable). | `0` |
| `--exclude-patterns` | Optional override for file exclusion. | `None` |
| `--create-dump-run-cmd`| Override the `create-dump` run command. | `None` |
| `-s`, `--steps` | Run specific steps or aliases. | All steps |
| `--test-cov-threshold`| Pytest coverage threshold (0=disable). | `85` |
| `--git-push` | Enable git commit/push in the `git` step. | `False` |
| `-es`, `--enable-security`| Enable security scan step. | `False` |
| `-eda`, `--enable-dep-audit`| Enable dependency audit step. | `False` |
| `--version` | Show program's version number and exit. | `N/A` |

### Workflow Steps

The workflow is composed of several steps, each of which can be run independently or as part of a larger sequence.

| Step ID | Alias(es) | Description |
|---|---|---|
| `step1` | `delete_dump`, `delete_dumps` | Delete old dumps (prune artifacts). |
| `step2` | `reformat`, `reformat_code` | Reformat code (ruff, autoimport, etc.). |
| `step2.5`| `pytest`, `test`, `tests` | Run pytest suite. |
| `step3` | `clean_caches`, `clean` | Clean caches (remove temporary files). |
| `step3.5`| `security`, `scan` | Security scan (bandit, safety). |
| `step4` | `backup` | Backup project (tar/zip). |
| `step5` | `create_dump`, `dump`, `dumps`| Generate dumps using the `create-dump` tool. |
| `step6` | `git`, `commit` | Commit hygiene snapshot to git. |
| `step6.5`| `audit`, `dep_audit` | Dependency vulnerability audit (pip-audit). |



---

## 🏗️ Architecture

The `routine-workflow` tool is designed with a clear separation of concerns, making it easy to maintain and extend.

### Directory Structure

```
src/routine_workflow/
├── __init__.py
├── banner.py           # ASCII art for the CLI
├── cli.py              # CLI argument parsing and entrypoint
├── config.py           #
├── defaults.py         # Default values for configuration
├── lock.py             # Concurrency locking mechanism
├── runner.py           # Core workflow orchestration logic
├── steps/              # Individual workflow steps
│   ├── __init__.py
│   ├── backup.py
│   ├── clean.py
│   └── ...
└── utils.py            # Shared utility functions
```

### Core Logic Flow

1.  **CLI Parsing**: The `cli.py` module parses all command-line arguments and builds a `WorkflowConfig` object.
2.  **Runner Initialization**: The `WorkflowRunner` is initialized with the configuration and the requested steps.
3.  **Locking**: The runner acquires a file-based lock to prevent concurrent runs.
4.  **Step Execution**: The runner iterates through the requested steps and executes them in order.
5.  **Logging**: Each step logs its progress to both the console and a rotating log file.
6.  **Cleanup**: The runner releases the lock and exits with a status code.

---

## 🗺️ Roadmap

- [ ] Add support for custom plugins/steps
- [ ] Implement a more sophisticated logging system
- [ ] Add more tests for edge cases

---

## 🤝 Contributing & License

Contributions are welcome! Please see the `CONTRIBUTING.md` file for more details.

This project is licensed under the terms of the **MIT** license.

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