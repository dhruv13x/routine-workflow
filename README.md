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

<!-- Usage -->
![Downloads](https://img.shields.io/pypi/dm/routine-workflow.svg)
![OS](https://img.shields.io/badge/os-Linux%20%7C%20macOS%20%7C%20Windows-blue.svg)
[![Python Versions](https://img.shields.io/pypi/pyversions/routine-workflow.svg)](https://pypi.org/project/routine-workflow/)

<!-- License -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

# Routine Workflow

**Production-grade automation for repository hygiene: code reformatting, cache cleaning, backups, dumps orchestration, and security auditing.**

`routine_workflow` is a robust, "batteries-included" Python tool designed to automate the mundane but critical maintenance tasks of your repository. Whether running in a CI pipeline or on a local developer machine, it ensures your project stays clean, secure, and well-formatted with a single command.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- `pip`

### Installation

Install from PyPI with a single command:

```bash
pip install routine-workflow
```

> **Tip**
> For an enhanced CLI experience with rich formatting and colors, install with the `rich` extra:
> `pip install "routine-workflow[rich]"`

### Usage Example

Run the default workflow in **safe mode** (Dry-Run):

```bash
routine-workflow
```

Execute the full workflow (Real Run):

```bash
routine-workflow -nd -y
```

Run specific steps using **Aliases**:

```bash
routine-workflow -s reformat clean backup -nd
```

---

## ✨ Key Features

- **🛡️ Safe by Default**: Ships with `dry-run` enabled to prevent accidental changes.
- **⚙️ Extensible Step Runner**: Run steps in any order, repeat them, or run a custom selection.
- **🧩 Alias-Driven**: Use intuitive aliases like `reformat`, `clean`, `pytest`, or `audit`.
- **⚡ Parallel Execution**: Utilizes multi-core processing for supported tasks to save time.
- **✅ Integrated Testing**: Run your `pytest` suite as part of the hygiene workflow.
- **🔒 Concurrency Safe**: Robust file-based locking prevents multiple instances from stepping on each other.
- **🔍 Security & Auditing**: **God Level** integration of security scans and dependency auditing.
- **📝 Advanced Logging**: JSON output, log rotation, and configurable verbosity levels.
- **✍️ Git Integration**: Automatically commit and push a hygiene snapshot after a successful run.

---

## ⚙️ Configuration & Advanced Usage

### Environment Variables

You can configure defaults via environment variables or a `.env` file (if supported by your environment loader).

| Variable | Description | Default |
|---|---|---|
| `PROJECT_ROOT` | Root directory of the project. | `CWD` |
| `LOG_DIR` | Directory for log files. | `/sdcard/tools/logs` |
| `LOCK_DIR` | Directory for the lock file. | `/tmp/routine_workflow.lock` |
| `LOCK_TTL` | Lock time-to-live in seconds. | `3600` |
| `WORKFLOW_TIMEOUT`| Overall workflow timeout in seconds. | `0` (Disabled) |
| `FAIL_ON_BACKUP` | Set to `1` to fail if backup fails. | `0` |
| `GIT_PUSH` | Set to `1` to enable git push. | `0` |
| `ENABLE_SECURITY` | Set to `1` to enable security scans. | `0` |
| `ENABLE_DEP_AUDIT`| Set to `1` to enable dependency audit. | `0` |

### CLI Arguments

Below is the complete list of arguments available in `routine-workflow`:

| Flag | Description | Default |
|---|---|---|
| `-p`, `--project-root` | Path to the project root. | `CWD` |
| `-l`, `--log-dir` | Directory to write logs. | `/sdcard/tools/logs` |
| `--log-file` | Optional single log file path. | `None` |
| `--lock-dir` | Directory for lock file. | `/tmp/routine_workflow.lock` |
| `--lock-ttl` | Lock eviction TTL in seconds (0=disable). | `3600` |
| `--log-level` | Logging verbosity (DEBUG, INFO, etc.). | `INFO` |
| `--log-format` | Log format (text or json). | `text` |
| `--fail-on-backup` | Exit if backup step fails. | `False` |
| `-y`, `--yes` | Auto-confirm prompts. | `False` |
| `-d`, `--dry-run` | Dry-run mode (default). | `True` |
| `-nd`, `--no-dry-run` | Disable dry-run (perform real execution). | `False` |
| `-w`, `--workers` | Parallel workers. | `min(8, CPU)` |
| `-t`, `--workflow-timeout`| Overall timeout in seconds. | `0` |
| `-s`, `--steps` | Specific steps/aliases to run. | All |
| `--test-cov-threshold` | Pytest coverage threshold. | `85` |
| `--git-push` | Enable git commit/push in step 6. | `False` |
| `-es`, `--enable-security`| Enable security scan (step 3.5). | `False` |
| `-eda`, `--enable-dep-audit`| Enable dependency audit (step 6.5). | `False` |
| `--version` | Show program's version. | `N/A` |

---

## 🏗️ Architecture

The `routine-workflow` follows a clean `src/` layout with modular components.

```text
src/routine_workflow/
├── __init__.py
├── banner.py           # CLI Banner & Art
├── cli.py              # Entry point & Argument Parsing
├── config.py           # Configuration Dataclass
├── defaults.py         # Default Settings
├── lock.py             # Concurrency Control
├── runner.py           # Workflow Orchestrator
├── steps/              # Modular Step Definitions
│   ├── step1.py        # Delete Dumps
│   ├── step2.py        # Reformat Code
│   ├── step2_5.py      # Pytest Runner
│   ├── step3.py        # Clean Caches
│   ├── step3_5.py      # Security Scan
│   ├── step4.py        # Backup
│   ├── step5.py        # Create Dumps
│   ├── step6.py        # Git Operations
│   └── step6_5.py      # Dependency Audit
└── utils.py            # Helpers
```

**Core Flow:**
1. **Config Loading**: Loads defaults, env vars, and CLI args into a `WorkflowConfig` object.
2. **Lock Acquisition**: Ensures only one instance runs via `lock.py`.
3. **Step Resolution**: Maps requested aliases (e.g., `audit`) to step modules (e.g., `step6_5.py`).
4. **Execution**: The `WorkflowRunner` executes steps sequentially, handling logging and errors.
5. **Report**: Generates a summary of the run.

---

## 🗺️ Roadmap

- [x] **Foundation**: Robust CLI, Logging, and Locking mechanisms.
- [x] **The Standard**: Core hygiene steps (Format, Clean, Backup).
- [x] **The Ecosystem**: Integration with `pytest`, `ruff`, and `create-dump`.
- [x] **Security**: Dependency auditing and security scanning.
- [ ] **The Vision**: Plugin system for custom user-defined steps.
- [ ] **The Sandbox**: Dockerized ephemeral environments for risky steps.

---

## 🤝 Contributing & License

We welcome contributions! Please see `CONTRIBUTING.md` (if available) or open a PR.

**License**: This project is licensed under the **MIT License**.
