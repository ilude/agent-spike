"""Authentication and user models.

Models for:
- User: Core user account
- UserSettings: Per-user preferences and API keys
- Invite: User invitation tokens
- UserContent: Links users to content library items
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, EmailStr


class UserRole:
    """User role constants."""
    ADMIN = "admin"
    USER = "user"


class OAuthProvider(BaseModel):
    """OAuth provider link for a user."""
    provider: str  # "google", "github"
    provider_id: str
    email: Optional[str] = None
    linked_at: datetime = Field(default_factory=datetime.now)


class User(BaseModel):
    """User account."""
    id: Optional[str] = None
    email: EmailStr
    password_hash: Optional[str] = None  # None for OAuth-only users
    display_name: str
    role: str = UserRole.USER
    oauth_providers: list[OAuthProvider] = Field(default_factory=list)
    email_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None

    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN


class UserCreate(BaseModel):
    """Request model for creating a user."""
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Request model for updating user profile."""
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    """Request model for changing password."""
    current_password: str
    new_password: str


class UserPublic(BaseModel):
    """Public user info (no sensitive data)."""
    id: str
    email: str
    display_name: str
    role: str
    oauth_providers: list[str] = Field(default_factory=list)  # Just provider names
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "UserPublic":
        """Create public view from full user."""
        return cls(
            id=user.id or "",
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            oauth_providers=[p.provider for p in user.oauth_providers],
            created_at=user.created_at,
        )


class UserSettings(BaseModel):
    """Per-user settings and preferences."""
    id: Optional[str] = None
    user_id: str

    # API keys (encrypted in DB)
    api_keys: dict[str, str] = Field(default_factory=dict)
    # e.g., {"anthropic": "sk-ant-...", "openai": "sk-..."}

    # Visible models in dropdown
    visible_models: list[str] = Field(default_factory=list)

    # Preferences
    preferences: dict[str, Any] = Field(default_factory=dict)
    # e.g., {"default_model": "...", "theme": "dark", "enable_rag": True}

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Invite(BaseModel):
    """User invitation."""
    id: Optional[str] = None
    token: str
    email: Optional[EmailStr] = None  # Pre-set email or None for open invite
    created_by: str  # User ID of inviter
    expires_at: datetime
    used_at: Optional[datetime] = None
    used_by: Optional[str] = None  # User ID who used the invite
    created_at: datetime = Field(default_factory=datetime.now)

    def is_valid(self) -> bool:
        """Check if invite is still valid."""
        return self.used_at is None and datetime.now() < self.expires_at


class UserContent(BaseModel):
    """Links a user to content in the shared pool.

    Content (videos, articles) is stored once; users have their own
    library pointing to shared content.
    """
    id: Optional[str] = None
    user_id: str
    content_type: str  # "video", "article"
    content_id: str  # ID in the content table (video_id, article_id)
    added_at: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None  # User's personal notes
    tags: list[str] = Field(default_factory=list)  # User's personal tags


class SystemConfig(BaseModel):
    """System-wide configuration stored in SurrealDB."""
    id: Optional[str] = None
    key: str
    value: str
    source: str = "db"  # "db" or "env" (for UI display)
    updated_at: datetime = Field(default_factory=datetime.now)


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # User ID
    email: str
    role: str
    exp: datetime


class TokenResponse(BaseModel):
    """Response model for login/token endpoints."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds
    user: UserPublic
