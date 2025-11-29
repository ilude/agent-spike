"""Unified configuration manager with hierarchy: .env → SurrealDB → defaults.

This module provides a centralized way to access configuration values
that supports:
1. Infrastructure-as-code via .env (always takes precedence)
2. Runtime configuration via SurrealDB (UI-editable)
3. Sensible hardcoded defaults (app works out of the box)

Usage:
    from compose.lib.config_manager import config

    # Synchronous access (env + defaults only, no DB)
    value = config.get("ANTHROPIC_API_KEY")

    # Async access (full hierarchy including DB)
    value = await config.get_async("ANTHROPIC_API_KEY")

    # Bulk access
    all_config = await config.get_all_async()
"""

import logging
import os
import secrets
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from compose.lib.defaults import DEFAULTS, SENSITIVE_KEYS, get_default

logger = logging.getLogger(__name__)


def _find_git_root(start_path: Optional[Path] = None) -> Path:
    """Walk up directory tree to find .git/ folder."""
    current = start_path or Path.cwd()
    current = current.resolve()

    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    raise FileNotFoundError("No .git directory found in any parent directory")


def _coerce_type(value: str, default: Any) -> Any:
    """Coerce string value to match the type of the default.

    Args:
        value: String value from env/db
        default: Default value (determines target type)

    Returns:
        Value coerced to appropriate type
    """
    if default is None:
        return value

    if isinstance(default, bool):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(value)
        except ValueError:
            return default
    return value


class ConfigManager:
    """Manages configuration with .env → SurrealDB → defaults hierarchy.

    The manager loads .env on initialization and provides both sync
    and async access methods.
    """

    def __init__(self):
        """Initialize the config manager and load .env."""
        self._env_loaded = False
        self._db_cache: dict[str, Any] = {}
        self._db_cache_loaded = False
        self._load_env()

    def _load_env(self) -> None:
        """Load .env file from git root."""
        if self._env_loaded:
            return

        try:
            git_root = _find_git_root()
            env_path = git_root / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=True)
                logger.debug(f"Loaded .env from {env_path}")
            else:
                logger.debug(f"No .env file found at {env_path}")
        except FileNotFoundError:
            logger.warning("Could not find git root, .env not loaded")

        self._env_loaded = True

        # Generate JWT secret if not set
        if not os.getenv("JWT_SECRET_KEY"):
            jwt_secret = secrets.token_urlsafe(32)
            os.environ["JWT_SECRET_KEY"] = jwt_secret
            logger.info("Generated new JWT_SECRET_KEY")

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value synchronously (.env → defaults only).

        This method does NOT check SurrealDB. Use get_async() for
        full hierarchy support.

        Args:
            key: Configuration key
            default: Override default (uses DEFAULTS if not provided)

        Returns:
            Configuration value
        """
        # Check .env first
        env_value = os.getenv(key)
        if env_value is not None:
            default_val = default if default is not None else get_default(key)
            return _coerce_type(env_value, default_val)

        # Fall back to provided default or DEFAULTS
        if default is not None:
            return default
        return get_default(key)

    async def get_async(self, key: str, default: Any = None) -> Any:
        """Get config value with full hierarchy (.env → SurrealDB → defaults).

        Args:
            key: Configuration key
            default: Override default (uses DEFAULTS if not provided)

        Returns:
            Configuration value
        """
        # Check .env first (always wins per IaC requirements)
        env_value = os.getenv(key)
        if env_value is not None:
            default_val = default if default is not None else get_default(key)
            return _coerce_type(env_value, default_val)

        # Check SurrealDB cache
        if not self._db_cache_loaded:
            await self._load_db_cache()

        if key in self._db_cache:
            default_val = default if default is not None else get_default(key)
            return _coerce_type(str(self._db_cache[key]), default_val)

        # Fall back to provided default or DEFAULTS
        if default is not None:
            return default
        return get_default(key)

    async def _load_db_cache(self) -> None:
        """Load all system_config values from SurrealDB into cache."""
        if self._db_cache_loaded:
            return

        try:
            from compose.services.surrealdb.driver import execute_query

            result = await execute_query("SELECT * FROM system_config")
            if result and isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and "key" in item and "value" in item:
                        self._db_cache[item["key"]] = item["value"]
            logger.debug(f"Loaded {len(self._db_cache)} config values from SurrealDB")
        except Exception as e:
            logger.warning(f"Could not load config from SurrealDB: {e}")

        self._db_cache_loaded = True

    def invalidate_cache(self) -> None:
        """Invalidate the DB cache to force reload on next access."""
        self._db_cache = {}
        self._db_cache_loaded = False

    async def get_all_async(self) -> dict[str, Any]:
        """Get all configuration values with full hierarchy.

        Returns:
            Dictionary of all config keys and their resolved values
        """
        result = {}
        for key in DEFAULTS:
            result[key] = await self.get_async(key)
        return result

    def get_all_sync(self) -> dict[str, Any]:
        """Get all configuration values synchronously (.env + defaults only).

        Returns:
            Dictionary of all config keys and their resolved values
        """
        result = {}
        for key in DEFAULTS:
            result[key] = self.get(key)
        return result

    async def set_async(self, key: str, value: Any) -> None:
        """Set a config value in SurrealDB.

        Note: This does NOT modify .env. Values set here will be
        overridden by .env on restart (IaC pattern).

        Args:
            key: Configuration key
            value: Value to set
        """
        try:
            from compose.services.surrealdb.driver import execute_query

            # Upsert the config value
            await execute_query(
                """
                UPSERT system_config:$key SET
                    key = $key,
                    value = $value,
                    updated_at = time::now()
                """,
                {"key": key, "value": str(value)},
            )

            # Update cache
            self._db_cache[key] = value
            logger.debug(f"Set config {key} in SurrealDB")

        except Exception as e:
            logger.error(f"Failed to set config {key}: {e}")
            raise

    async def delete_async(self, key: str) -> None:
        """Delete a config value from SurrealDB.

        Args:
            key: Configuration key to delete
        """
        try:
            from compose.services.surrealdb.driver import execute_query

            await execute_query(
                "DELETE system_config WHERE key = $key",
                {"key": key},
            )

            # Update cache
            self._db_cache.pop(key, None)
            logger.debug(f"Deleted config {key} from SurrealDB")

        except Exception as e:
            logger.error(f"Failed to delete config {key}: {e}")
            raise

    async def export_to_env(self, keys: Optional[list[str]] = None) -> str:
        """Export current config values to .env format.

        Args:
            keys: Specific keys to export (all if None)

        Returns:
            String in .env format
        """
        all_config = await self.get_all_async()
        lines = []

        export_keys = keys if keys else sorted(all_config.keys())
        for key in export_keys:
            if key in all_config:
                value = all_config[key]
                # Quote strings with spaces
                if isinstance(value, str) and " " in value:
                    lines.append(f'{key}="{value}"')
                else:
                    lines.append(f"{key}={value}")

        return "\n".join(lines)

    async def write_to_env_file(self, keys: Optional[list[str]] = None) -> Path:
        """Write config values to .env file.

        This merges with existing .env content, updating only
        the specified keys.

        Args:
            keys: Specific keys to write (all if None)

        Returns:
            Path to the .env file
        """
        git_root = _find_git_root()
        env_path = git_root / ".env"

        # Read existing .env content
        existing_lines: list[str] = []
        existing_keys: set[str] = set()
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if "=" in line and not line.startswith("#"):
                        key = line.split("=", 1)[0]
                        existing_keys.add(key)
                    existing_lines.append(line)

        # Get current values
        all_config = await self.get_all_async()
        export_keys = set(keys) if keys else set(all_config.keys())

        # Update existing lines
        updated_lines = []
        for line in existing_lines:
            if "=" in line and not line.startswith("#"):
                key = line.split("=", 1)[0]
                if key in export_keys and key in all_config:
                    value = all_config[key]
                    if isinstance(value, str) and " " in value:
                        updated_lines.append(f'{key}="{value}"')
                    else:
                        updated_lines.append(f"{key}={value}")
                    export_keys.discard(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # Add new keys
        if export_keys:
            updated_lines.append("")
            updated_lines.append("# Added by config manager")
            for key in sorted(export_keys):
                if key in all_config:
                    value = all_config[key]
                    if isinstance(value, str) and " " in value:
                        updated_lines.append(f'{key}="{value}"')
                    else:
                        updated_lines.append(f"{key}={value}")

        # Write back
        with open(env_path, "w") as f:
            f.write("\n".join(updated_lines))
            f.write("\n")

        logger.info(f"Updated .env file at {env_path}")
        return env_path

    def is_sensitive(self, key: str) -> bool:
        """Check if a key contains sensitive data."""
        return key in SENSITIVE_KEYS

    def mask_value(self, key: str, value: Any) -> str:
        """Mask sensitive values for display.

        Args:
            key: Configuration key
            value: Value to potentially mask

        Returns:
            Masked or original value as string
        """
        if not self.is_sensitive(key):
            return str(value)

        str_value = str(value)
        if not str_value:
            return ""
        if len(str_value) <= 8:
            return "*" * len(str_value)
        return str_value[:4] + "*" * (len(str_value) - 8) + str_value[-4:]


# Singleton instance
config = ConfigManager()


# Convenience functions for backward compatibility
def get_config(key: str, default: Any = None) -> Any:
    """Get config value synchronously."""
    return config.get(key, default)


async def get_config_async(key: str, default: Any = None) -> Any:
    """Get config value asynchronously with full hierarchy."""
    return await config.get_async(key, default)
