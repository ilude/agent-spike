"""Default configuration values for the application.

All hardcoded defaults live here. The app should be fully functional
with these defaults (minus external API calls requiring keys).

Config hierarchy: .env → SurrealDB → these defaults
"""

from typing import Any

# =============================================================================
# Configuration Defaults
# =============================================================================

DEFAULTS: dict[str, Any] = {
    # -------------------------------------------------------------------------
    # Database - SurrealDB
    # -------------------------------------------------------------------------
    "SURREALDB_URL": "ws://localhost:8000",
    "SURREALDB_USER": "root",
    "SURREALDB_PASSWORD": "root",
    "SURREALDB_NAMESPACE": "agent_spike",
    "SURREALDB_DATABASE": "graph",

    # -------------------------------------------------------------------------
    # Object Storage - MinIO
    # -------------------------------------------------------------------------
    "MINIO_URL": "http://localhost:9000",
    "MINIO_ACCESS_KEY": "minioadmin",
    "MINIO_SECRET_KEY": "minioadmin",
    "MINIO_BUCKET": "vectors",

    # -------------------------------------------------------------------------
    # AI Services
    # -------------------------------------------------------------------------
    "INFINITY_URL": "http://localhost:7997",
    "OLLAMA_URL": "http://localhost:11434",
    "DOCLING_URL": "http://localhost:5001",

    # -------------------------------------------------------------------------
    # External API Keys (empty = not configured)
    # -------------------------------------------------------------------------
    "ANTHROPIC_API_KEY": "",
    "OPENAI_API_KEY": "",
    "OPENROUTER_API_KEY": "",
    "YOUTUBE_API_KEY": "",

    # -------------------------------------------------------------------------
    # Auth Settings
    # -------------------------------------------------------------------------
    "JWT_SECRET_KEY": "",  # Generated on first boot if empty
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRY_DAYS": 365,  # 1 year sessions

    # -------------------------------------------------------------------------
    # Registration Settings
    # -------------------------------------------------------------------------
    "REGISTRATION_OPEN": False,  # After first user, admin controls this
    "REQUIRE_EMAIL_VERIFICATION": False,  # Basic auth for v1

    # -------------------------------------------------------------------------
    # OAuth Providers (empty = disabled)
    # -------------------------------------------------------------------------
    "OAUTH_GOOGLE_CLIENT_ID": "",
    "OAUTH_GOOGLE_CLIENT_SECRET": "",
    "OAUTH_GITHUB_CLIENT_ID": "",
    "OAUTH_GITHUB_CLIENT_SECRET": "",

    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    "ENABLE_RAG": True,
    "ENABLE_MEMORY": True,
    "ENABLE_WEBSEARCH": True,
    "ENABLE_IMAGE_GEN": True,
    "ENABLE_SANDBOX": True,

    # -------------------------------------------------------------------------
    # Model Defaults
    # -------------------------------------------------------------------------
    "DEFAULT_CHAT_MODEL": "moonshotai/kimi-k2:free",
    "DEFAULT_EMBEDDING_MODEL": "bge-m3",
    "DEFAULT_CHAT_STYLE": "default",

    # -------------------------------------------------------------------------
    # Export Settings
    # -------------------------------------------------------------------------
    "ENABLE_LLM_FILENAMES": False,  # Use AI to generate export filenames
    "FILENAME_GENERATION_MODEL": "ollama:llama3.2",  # Model for filename generation

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    "APP_NAME": "Mentat",
    "APP_URL": "http://localhost:5173",
    "API_URL": "http://localhost:8000",

    # -------------------------------------------------------------------------
    # Proxy Settings (optional)
    # -------------------------------------------------------------------------
    "WEBSHARE_PROXY_USERNAME": "",
    "WEBSHARE_PROXY_PASSWORD": "",
    "WEBSHARE_API_TOKEN": "",

    # -------------------------------------------------------------------------
    # Workflow Automation (optional)
    # -------------------------------------------------------------------------
    "N8N_URL": "",
    "N8N_ENCRYPTION_KEY": "",
}


# =============================================================================
# Config Categories (for UI organization)
# =============================================================================

CONFIG_CATEGORIES = {
    "database": [
        "SURREALDB_URL",
        "SURREALDB_USER",
        "SURREALDB_PASSWORD",
        "SURREALDB_NAMESPACE",
        "SURREALDB_DATABASE",
    ],
    "storage": [
        "MINIO_URL",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_BUCKET",
    ],
    "ai_services": [
        "INFINITY_URL",
        "OLLAMA_URL",
        "DOCLING_URL",
    ],
    "api_keys": [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "YOUTUBE_API_KEY",
    ],
    "auth": [
        "JWT_SECRET_KEY",
        "JWT_ALGORITHM",
        "JWT_EXPIRY_DAYS",
        "REGISTRATION_OPEN",
        "REQUIRE_EMAIL_VERIFICATION",
    ],
    "oauth": [
        "OAUTH_GOOGLE_CLIENT_ID",
        "OAUTH_GOOGLE_CLIENT_SECRET",
        "OAUTH_GITHUB_CLIENT_ID",
        "OAUTH_GITHUB_CLIENT_SECRET",
    ],
    "features": [
        "ENABLE_RAG",
        "ENABLE_MEMORY",
        "ENABLE_WEBSEARCH",
        "ENABLE_IMAGE_GEN",
        "ENABLE_SANDBOX",
    ],
    "defaults": [
        "DEFAULT_CHAT_MODEL",
        "DEFAULT_EMBEDDING_MODEL",
        "DEFAULT_CHAT_STYLE",
    ],
    "export": [
        "ENABLE_LLM_FILENAMES",
        "FILENAME_GENERATION_MODEL",
    ],
    "app": [
        "APP_NAME",
        "APP_URL",
        "API_URL",
    ],
    "proxy": [
        "WEBSHARE_PROXY_USERNAME",
        "WEBSHARE_PROXY_PASSWORD",
        "WEBSHARE_API_TOKEN",
    ],
    "workflow": [
        "N8N_URL",
        "N8N_ENCRYPTION_KEY",
    ],
}


# =============================================================================
# Sensitive Keys (should be masked in UI)
# =============================================================================

SENSITIVE_KEYS = {
    "SURREALDB_PASSWORD",
    "MINIO_SECRET_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "YOUTUBE_API_KEY",
    "JWT_SECRET_KEY",
    "OAUTH_GOOGLE_CLIENT_SECRET",
    "OAUTH_GITHUB_CLIENT_SECRET",
    "WEBSHARE_PROXY_PASSWORD",
    "WEBSHARE_API_TOKEN",
    "N8N_ENCRYPTION_KEY",
}


def get_default(key: str) -> Any:
    """Get the default value for a config key.

    Args:
        key: Configuration key name

    Returns:
        Default value, or None if key not found
    """
    return DEFAULTS.get(key)


def is_sensitive(key: str) -> bool:
    """Check if a config key contains sensitive data.

    Args:
        key: Configuration key name

    Returns:
        True if the key contains sensitive data
    """
    return key in SENSITIVE_KEYS


def get_category(key: str) -> str | None:
    """Get the category for a config key.

    Args:
        key: Configuration key name

    Returns:
        Category name, or None if not categorized
    """
    for category, keys in CONFIG_CATEGORIES.items():
        if key in keys:
            return category
    return None
