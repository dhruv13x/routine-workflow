# routine_workflow/defaults.py

"""Default exclude patterns for file discovery."""

from typing import List


def default_exclude_patterns() -> List[str]:
    return [
        "venv/*",
        ".venv/*",
        ".git/*",
        "__pycache__/*",
        "*/conftest.py",
        "packages/*/tests/conftest.py",
        "services/forwarder_bot/bot/__main__.py",
        "packages/platform_core/src/platform_core/utils/decorators/auth.py",
        "packages/platform_core/src/platform_core/rate_limiter/facade.py",
        "packages/platform_core/src/platform_core/core/app_context.py",
        "packages/platform_core/src/platform_core/db/models/connections.py",
        "packages/platform_core/tests/conftest.py",
        "scripts/check_imports.py",
        "services/forwarder_bot/bot/services/job_service.py",
        "services/forwarder_bot/bot/services/config_resolver.py",
        "services/forwarder_bot/bot/core/app_context.py",
        "services/forwarder_bot/tests/conftest.py",
    ]