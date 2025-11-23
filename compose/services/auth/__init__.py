"""Authentication service package."""

from .models import (
    Invite,
    OAuthProvider,
    PasswordChange,
    SystemConfig,
    TokenPayload,
    TokenResponse,
    User,
    UserContent,
    UserCreate,
    UserLogin,
    UserPublic,
    UserRole,
    UserSettings,
    UserUpdate,
)
from .service import AuthService, get_auth_service

__all__ = [
    # Models
    "Invite",
    "OAuthProvider",
    "PasswordChange",
    "SystemConfig",
    "TokenPayload",
    "TokenResponse",
    "User",
    "UserContent",
    "UserCreate",
    "UserLogin",
    "UserPublic",
    "UserRole",
    "UserSettings",
    "UserUpdate",
    # Service
    "AuthService",
    "get_auth_service",
]
