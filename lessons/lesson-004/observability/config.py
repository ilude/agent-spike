"""Configuration for Pydantic Logfire observability."""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class LogfireConfig:
    """Logfire configuration."""

    token: Optional[str] = None
    project_name: str = "agent-spike"
    enabled: bool = True
    console: bool = True  # Also log to console for debugging


def get_logfire_config() -> LogfireConfig:
    """
    Load Logfire configuration from environment variables.

    Returns:
        LogfireConfig with settings from environment or defaults.
    """
    token = os.getenv("LOGFIRE_TOKEN")
    project_name = os.getenv("LOGFIRE_PROJECT_NAME", "agent-spike")
    enabled = os.getenv("LOGFIRE_ENABLED", "true").lower() == "true"

    return LogfireConfig(
        token=token, project_name=project_name, enabled=enabled
    )


def is_logfire_enabled() -> bool:
    """
    Check if Logfire is enabled.

    Returns:
        True if Logfire should be enabled, False otherwise.
    """
    config = get_logfire_config()
    return config.enabled
