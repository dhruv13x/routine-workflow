<div align="center">
  <img src="https://raw.githubusercontent.com/dhruv13x/routine-workflow/main/routine-workflow_logo.png" alt="routine-workflow logo" width="200"/>
</div>

<div align="center">

<!-- Package Info -->
[![PyPI version](https://img.shields.io/pypi/v/routine-workflow.svg)](https://pypi.org/project/routine-workflow/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
![Wheel](https://img.shields.io/pypi/wheel/routine-workflow.svg)
[![Release](https://img.shields.io/badge/release-PyPI-blue)](https://pypi.org/project/routine-workflow/)

<!-- Build & Quality -->
[![Build status](https://github.com/dhruv13x/routine-workflow/actions/workflows/publish.yml/badge.svg)](https://github.com/dhruv13x/routine-workflow/actions/workflows/publish.yml)
[![Codecov](https://codecov.io/gh/dhruv13x/routine-workflow/graph/badge.svg)](https://codecov.io/gh/dhruv13x/routine-workflow)
[![Test Coverage](https://img.shields.io/badge/coverage-95%25%2B-brightgreen.svg)](https://github.com/dhruv13x/routine-workflow/actions/workflows/test.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linting-ruff-yellow.svg)](https://github.com/astral-sh/ruff)
![Security](https://img.shields.io/badge/security-CodeQL-blue.svg)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/dhruv13x/routine-workflow/graphs/commit-activity)

<!-- Usage -->
![Downloads](https://img.shields.io/pypi/dm/routine-workflow.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

# Routine Workflow

**Production-grade automation for repository hygiene: code reformatting, cache cleaning, backups, dumps orchestration, and security auditing.**

`routine_workflow` is a robust, "batteries-included" Python tool designed to automate the mundane but critical maintenance tasks of your repository. Whether running in a CI pipeline or on a local developer machine, it ensures your project stays clean, secure, and well-formatted with a single command.

---

## ⚡ Quick Start (The "5-Minute Rule")

### Prerequisites
- **Python**: 3.9+
- **Pip**: Latest version recommended

### Installation

Install via pip:

```bash
pip install routine-workflow
```

### Run

Run the default workflow in **Dry-Run Mode** (Safe by default):

```bash
routine-workflow
```

To execute the **Full Workflow** (Real changes):

```bash
routine-workflow -nd -y
```

### Demo

Copy-paste this snippet to see it in action (Dry Run):

```bash
# 1. Install
pip install routine-workflow

# 2. Run with rich interface (safe mode)
routine-workflow

# 3. View help for more options
routine-workflow --help
```

---

## ✨ Features

### 🛠️ Core Essentials
- **Code Reformatting**: Automatically formats code using `ruff` and `isort`.
- **Cache Cleaning**: Wipes `__pycache__`, `.pytest_cache`, and other temporary files.
- **Backups & Dumps**: Orchestrates safe backups and code dumps before changes.
- **Git Integration**: Auto-commits and pushes a "hygiene snapshot" after success.

### 🛡️ Security & Quality
- **Security Audits**: Runs `bandit` and `safety` to catch vulnerabilities.
- **Dependency Auditing**: Checks for outdated or insecure dependencies.
- **Test Integration**: Runs `pytest` suite with coverage enforcement.

### 🚀 Performance & UX
- **Parallel Execution**: Uses multi-processing for CPU-bound tasks.
- **Interactive Mode**: Guided wizard (`-i`) for easy configuration.
- **Profiling**: Built-in performance profiling (`--profile`).
- **Rich Logging**: JSON output, log rotation, and beautiful terminal UI.

---

## 🛠️ Configuration

Configure `routine-workflow` via **Environment Variables** (for CI/CD) or **CLI Arguments** (for local use).

### Environment Variables

| Variable | Description | Default | Required |
|---|---|---|---|
| `PROJECT_ROOT` | Root path of the target project. | `CWD` | No |
| `LOG_DIR` | Directory for log files. | `/sdcard/tools/logs` | No |
| `LOCK_DIR` | Directory for the execution lock file. | `/tmp/routine_workflow.lock` | No |
| `FAIL_ON_BACKUP`| Fail the workflow if backup fails (0/1). | `0` (False) | No |
| `GIT_PUSH` | Enable git push after hygiene (0/1). | `0` (False) | No |
| `ENABLE_SECURITY`| Enable security scanning steps (0/1). | `0` (False) | No |
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO). | `INFO` | No |

### CLI Arguments

| Flag | Description |
|---|---|
| `-p`, `--project-root` | Path to the project root. |
| `-nd`, `--no-dry-run` | **Execute real changes** (Disable dry-run). |
| `-y`, `--yes` | Auto-confirm all prompts. |
| `-s`, `--steps` | Run specific steps (e.g., `-s reformat backup`). |
| `-i`, `--interactive` | Launch interactive configuration wizard. |
| `-es`, `--enable-security`| Enable security scan step. |
| `-eda`, `--enable-dep-audit`| Enable dependency audit step. |
| `--install-pre-commit` | Install as a pre-commit hook. |

---

## 🏗️ Architecture

The project follows a modular, step-based architecture designed for extensibility and reliability.

### Directory Tree

```text
src/routine_workflow
├── __init__.py
├── banner.py           # CLI Art
├── cli.py              # Entry Point
├── config.py           # Configuration Model
├── runner.py           # Workflow Orchestrator
├── lock.py             # File-based Locking
├── steps/              # Modular Workflow Steps
│   ├── step1.py        # Delete Dumps
│   ├── step2.py        # Reformat
│   ├── step3.py        # Clean Caches
│   ├── step3_5.py      # Security Scan
│   ├── step4.py        # Backup
│   ├── step6.py        # Git Operations
│   └── ...
└── utils.py            # Helpers
```

### Data Flow

1.  **Init**: CLI parses args & env vars -> `WorkflowConfig`.
2.  **Lock**: Acquires file lock to prevent concurrent runs.
3.  **Plan**: `WorkflowRunner` resolves requested steps/aliases.
4.  **Execute**: Steps run sequentially (some parallelized internally).
5.  **Report**: Results logged to console and JSON log files.

---

## 🐞 Troubleshooting

### Common Issues

| Error Message | Possible Cause | Solution |
|---|---|---|
| `LockAcquisitionError` | Another instance is running or stale lock. | Wait or delete lock file at `/tmp/routine_workflow.lock`. |
| `CommandNotFoundError` | Missing external tool (e.g., `ruff`). | Ensure dev dependencies are installed (`pip install .[dev]`). |
| `BackupFailedError` | Disk space or permission issue. | Check `LOG_DIR` permissions and disk space. |

### Debug Mode

To see verbose output for debugging:

```bash
routine-workflow --log-level DEBUG
```

---

## 🤝 Contributing

We welcome contributions!

1.  **Fork** the repository.
2.  **Install** dev dependencies:
    ```bash
    pip install -e ".[dev]"
    ```
3.  **Run Tests**:
    ```bash
    pytest
    ```
4.  **Submit** a Pull Request.

See `CONTRIBUTING.md` (if available) for detailed guidelines.

---

## 🗺️ Roadmap

- [x] **Core**: CLI, Step Runner, Reformat, Clean, Backup.
- [x] **Security**: Bandit, Safety, Dependency Audit.
- [x] **Advanced**: Interactive Mode, Profiling, JSON Logging.
- [ ] **Upcoming**: 3rd Party Plugins, Webhooks (Slack/Discord), AI Refactoring.

See `ROADMAP.md` for the full vision.
