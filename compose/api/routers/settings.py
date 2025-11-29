"""Settings API endpoints.

Endpoints for user settings and admin configuration:
- GET /settings - Get current user's settings
- PUT /settings - Update current user's settings
- GET /settings/api-keys - Get user's API key status
- PUT /settings/api-keys - Update user's API keys
- GET /settings/models - Get visible models for user
- PUT /settings/models - Update visible models

Admin endpoints:
- GET /settings/system - Get system configuration
- PUT /settings/system - Update system configuration
- POST /settings/system/export - Export config to .env
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from compose.lib.config_manager import config
from compose.lib.defaults import CONFIG_CATEGORIES, DEFAULTS, SENSITIVE_KEYS
from compose.services.auth import User, get_auth_service
from compose.api.routers.auth import get_current_user, require_admin

router = APIRouter(prefix="/settings", tags=["settings"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ApiKeyStatus(BaseModel):
    """Status of an API key (configured or not)."""
    provider: str
    configured: bool
    masked_value: Optional[str] = None


class ApiKeysUpdate(BaseModel):
    """Update API keys request."""
    anthropic: Optional[str] = None
    openai: Optional[str] = None
    openrouter: Optional[str] = None
    youtube: Optional[str] = None


class ModelsUpdate(BaseModel):
    """Update visible models request."""
    visible_models: list[str]


class PreferencesUpdate(BaseModel):
    """Update preferences request."""
    default_model: Optional[str] = None
    default_style: Optional[str] = None
    enable_rag: Optional[bool] = None
    enable_memory: Optional[bool] = None


class UserSettingsResponse(BaseModel):
    """User settings response."""
    api_keys: list[ApiKeyStatus]
    visible_models: list[str]
    preferences: dict[str, Any]


class SystemConfigItem(BaseModel):
    """A single system config item."""
    key: str
    value: Any
    category: str
    is_sensitive: bool
    source: str  # "env" or "db" or "default"


class SystemConfigResponse(BaseModel):
    """System configuration response."""
    items: list[SystemConfigItem]
    categories: list[str]


class SystemConfigUpdate(BaseModel):
    """Update system configuration request."""
    key: str
    value: str


# =============================================================================
# Helper Functions
# =============================================================================


def _mask_key(value: str) -> str:
    """Mask an API key for display."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


async def _get_api_key_for_user(
    user_id: str,
    provider: str,
    env_key: str,
) -> tuple[str, str]:
    """Get API key for user with fallback to system key.

    Returns:
        Tuple of (key_value, source) where source is "user" or "system"
    """
    auth = get_auth_service()
    settings = await auth.get_user_settings(user_id)

    # Check user's key first
    if settings and settings.api_keys.get(provider):
        return settings.api_keys[provider], "user"

    # Fall back to system key
    system_key = config.get(env_key, "")
    if system_key:
        return system_key, "system"

    return "", "none"


# =============================================================================
# User Settings Endpoints
# =============================================================================


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    user: User = Depends(get_current_user),
):
    """Get current user's settings."""
    auth = get_auth_service()
    settings = await auth.get_user_settings(user.id)

    if not settings:
        settings = await auth.create_user_settings(user.id)

    # Build API key status list
    api_keys = []
    for provider, env_key in [
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
        ("youtube", "YOUTUBE_API_KEY"),
    ]:
        key_value, source = await _get_api_key_for_user(user.id, provider, env_key)
        api_keys.append(ApiKeyStatus(
            provider=provider,
            configured=bool(key_value),
            masked_value=_mask_key(key_value) if key_value else None,
        ))

    return UserSettingsResponse(
        api_keys=api_keys,
        visible_models=settings.visible_models,
        preferences=settings.preferences,
    )


@router.put("")
async def update_settings(
    preferences: PreferencesUpdate,
    user: User = Depends(get_current_user),
):
    """Update current user's preferences."""
    auth = get_auth_service()

    # Build preferences dict from non-None values
    prefs = {}
    if preferences.default_model is not None:
        prefs["default_model"] = preferences.default_model
    if preferences.default_style is not None:
        prefs["default_style"] = preferences.default_style
    if preferences.enable_rag is not None:
        prefs["enable_rag"] = preferences.enable_rag
    if preferences.enable_memory is not None:
        prefs["enable_memory"] = preferences.enable_memory

    await auth.update_user_settings(
        user_id=user.id,
        preferences=prefs,
    )

    return {"message": "Settings updated"}


@router.get("/api-keys", response_model=list[ApiKeyStatus])
async def get_api_keys(
    user: User = Depends(get_current_user),
):
    """Get API key status for current user."""
    api_keys = []
    for provider, env_key in [
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
        ("youtube", "YOUTUBE_API_KEY"),
    ]:
        key_value, source = await _get_api_key_for_user(user.id, provider, env_key)
        api_keys.append(ApiKeyStatus(
            provider=provider,
            configured=bool(key_value),
            masked_value=_mask_key(key_value) if key_value else None,
        ))

    return api_keys


@router.put("/api-keys")
async def update_api_keys(
    data: ApiKeysUpdate,
    user: User = Depends(get_current_user),
):
    """Update user's personal API keys.

    These override system keys for this user only.
    """
    auth = get_auth_service()

    keys = {}
    if data.anthropic is not None:
        keys["anthropic"] = data.anthropic
    if data.openai is not None:
        keys["openai"] = data.openai
    if data.openrouter is not None:
        keys["openrouter"] = data.openrouter
    if data.youtube is not None:
        keys["youtube"] = data.youtube

    await auth.update_user_settings(
        user_id=user.id,
        api_keys=keys,
    )

    return {"message": "API keys updated"}


@router.get("/models", response_model=list[str])
async def get_visible_models(
    user: User = Depends(get_current_user),
):
    """Get list of visible model IDs for current user."""
    auth = get_auth_service()
    settings = await auth.get_user_settings(user.id)

    if not settings:
        return []

    return settings.visible_models


@router.put("/models")
async def update_visible_models(
    data: ModelsUpdate,
    user: User = Depends(get_current_user),
):
    """Update list of visible models for current user."""
    auth = get_auth_service()

    await auth.update_user_settings(
        user_id=user.id,
        visible_models=data.visible_models,
    )

    return {"message": "Visible models updated"}


# =============================================================================
# Admin System Config Endpoints
# =============================================================================


@router.get("/system", response_model=SystemConfigResponse)
async def get_system_config(
    _: User = Depends(require_admin),
):
    """Get system configuration (admin only).

    Returns all config values with their sources (env/db/default).
    """
    import os
    from compose.lib.defaults import get_category

    items = []

    for key, default_value in DEFAULTS.items():
        # Determine source and value
        env_value = os.getenv(key)
        if env_value is not None:
            source = "env"
            value = env_value
        else:
            # Check DB (would need async lookup - simplified here)
            source = "default"
            value = default_value

        # Mask sensitive values
        is_sensitive = key in SENSITIVE_KEYS
        display_value = _mask_key(str(value)) if is_sensitive and value else value

        category = get_category(key) or "other"

        items.append(SystemConfigItem(
            key=key,
            value=display_value,
            category=category,
            is_sensitive=is_sensitive,
            source=source,
        ))

    categories = list(CONFIG_CATEGORIES.keys())

    return SystemConfigResponse(
        items=items,
        categories=categories,
    )


@router.put("/system")
async def update_system_config(
    data: SystemConfigUpdate,
    _: User = Depends(require_admin),
):
    """Update a system configuration value (admin only).

    Note: This saves to SurrealDB. If .env has this key,
    the .env value will override on restart.
    """
    if data.key not in DEFAULTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown config key: {data.key}",
        )

    await config.set_async(data.key, data.value)

    return {"message": f"Config {data.key} updated"}


@router.post("/system/export")
async def export_system_config(
    keys: Optional[list[str]] = None,
    _: User = Depends(require_admin),
):
    """Export system config to .env file (admin only).

    If keys is provided, only those keys are exported.
    Otherwise, all keys are exported.
    """
    env_path = await config.write_to_env_file(keys)

    return {
        "message": "Configuration exported to .env",
        "path": str(env_path),
    }


@router.get("/system/registration")
async def get_registration_settings(
    _: User = Depends(require_admin),
):
    """Get registration settings (admin only)."""
    return {
        "registration_open": config.get("REGISTRATION_OPEN", False),
        "require_email_verification": config.get("REQUIRE_EMAIL_VERIFICATION", False),
    }


@router.put("/system/registration")
async def update_registration_settings(
    registration_open: Optional[bool] = None,
    _: User = Depends(require_admin),
):
    """Update registration settings (admin only)."""
    if registration_open is not None:
        await config.set_async("REGISTRATION_OPEN", str(registration_open).lower())

    return {"message": "Registration settings updated"}
