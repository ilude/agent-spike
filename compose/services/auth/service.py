"""Authentication service for user management.

Handles:
- User registration and login
- Password hashing and verification
- JWT token generation and validation
- User CRUD operations
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from pydantic import EmailStr

from compose.lib.config_manager import config
from compose.services.surrealdb.driver import execute_query

from .models import (
    Invite,
    OAuthProvider,
    PasswordChange,
    TokenPayload,
    TokenResponse,
    User,
    UserCreate,
    UserPublic,
    UserRole,
    UserSettings,
    UserUpdate,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and user management."""

    def __init__(self):
        """Initialize the auth service."""
        pass

    # =========================================================================
    # Password Utilities
    # =========================================================================

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Bcrypt hash
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: Plain text password
            password_hash: Bcrypt hash to check against

        Returns:
            True if password matches
        """
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    # =========================================================================
    # JWT Token Utilities
    # =========================================================================

    def create_access_token(self, user: User) -> tuple[str, int]:
        """Create a JWT access token for a user.

        Args:
            user: User to create token for

        Returns:
            Tuple of (token, expires_in_seconds)
        """
        jwt_secret = config.get("JWT_SECRET_KEY")
        jwt_algorithm = config.get("JWT_ALGORITHM", "HS256")
        expiry_days = config.get("JWT_EXPIRY_DAYS", 365)

        expires_delta = timedelta(days=expiry_days)
        expires_at = datetime.now(timezone.utc) + expires_delta

        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
        }

        token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
        return token, int(expires_delta.total_seconds())

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenPayload if valid, None otherwise
        """
        jwt_secret = config.get("JWT_SECRET_KEY")
        jwt_algorithm = config.get("JWT_ALGORITHM", "HS256")

        try:
            payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
            return TokenPayload(
                sub=payload["sub"],
                email=payload["email"],
                role=payload["role"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None

    # =========================================================================
    # User Operations
    # =========================================================================

    async def get_user_count(self) -> int:
        """Get total number of users.

        Returns:
            Number of users in the database
        """
        result = await execute_query("SELECT count() FROM users GROUP ALL")
        if result and isinstance(result, list) and len(result) > 0:
            return result[0].get("count", 0)
        return 0

    async def is_first_user(self) -> bool:
        """Check if this would be the first user (for admin assignment).

        Returns:
            True if no users exist yet
        """
        count = await self.get_user_count()
        return count == 0

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User or None if not found
        """
        results = await execute_query(f"SELECT * FROM users:`{user_id}`")
        if not results:
            return None
        return self._user_from_db(results[0])

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: User email

        Returns:
            User or None if not found
        """
        results = await execute_query(
            "SELECT * FROM users WHERE email = $email",
            {"email": email.lower()},
        )
        if not results:
            return None
        return self._user_from_db(results[0])

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user.

        Args:
            data: User creation data

        Returns:
            Created user

        Raises:
            ValueError: If email already exists
        """
        # Check if email exists
        existing = await self.get_user_by_email(data.email)
        if existing:
            raise ValueError("Email already registered")

        # Check if first user (becomes admin)
        is_first = await self.is_first_user()
        role = UserRole.ADMIN if is_first else UserRole.USER

        user_id = str(uuid.uuid4())
        password_hash = self.hash_password(data.password)
        display_name = data.display_name or data.email.split("@")[0]

        query = """
        INSERT INTO users {
            id: $id,
            email: $email,
            password_hash: $password_hash,
            display_name: $display_name,
            role: $role,
            oauth_providers: [],
            email_verified: false,
            created_at: time::now(),
            updated_at: time::now()
        };
        """

        await execute_query(query, {
            "id": user_id,
            "email": data.email.lower(),
            "password_hash": password_hash,
            "display_name": display_name,
            "role": role,
        })

        # Create default user settings
        await self.create_user_settings(user_id)

        logger.info(f"Created user {user_id} with role {role}")

        return User(
            id=user_id,
            email=data.email.lower(),
            password_hash=password_hash,
            display_name=display_name,
            role=role,
            oauth_providers=[],
            email_verified=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User if authentication succeeds, None otherwise
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None

        if not user.password_hash:
            # OAuth-only user
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        # Update last login
        await execute_query(
            f"UPDATE users:`{user.id}` SET last_login_at = time::now()"
        )

        return user

    async def login(self, email: str, password: str) -> Optional[TokenResponse]:
        """Login a user and return tokens.

        Args:
            email: User email
            password: Plain text password

        Returns:
            TokenResponse if login succeeds, None otherwise
        """
        user = await self.authenticate(email, password)
        if not user:
            return None

        token, expires_in = self.create_access_token(user)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserPublic.from_user(user),
        )

    async def update_user(
        self,
        user_id: str,
        data: UserUpdate,
    ) -> Optional[User]:
        """Update user profile.

        Args:
            user_id: User ID
            data: Update data

        Returns:
            Updated user or None if not found
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        updates = ["updated_at = time::now()"]
        params = {}

        if data.display_name is not None:
            updates.append("display_name = $display_name")
            params["display_name"] = data.display_name

        if data.email is not None:
            # Check if email is already used
            existing = await self.get_user_by_email(data.email)
            if existing and existing.id != user_id:
                raise ValueError("Email already in use")
            updates.append("email = $email")
            params["email"] = data.email.lower()

        set_clause = ", ".join(updates)
        await execute_query(
            f"UPDATE users:`{user_id}` SET {set_clause}",
            params,
        )

        return await self.get_user_by_id(user_id)

    async def change_password(
        self,
        user_id: str,
        data: PasswordChange,
    ) -> bool:
        """Change user password.

        Args:
            user_id: User ID
            data: Password change data

        Returns:
            True if successful

        Raises:
            ValueError: If current password is wrong
        """
        user = await self.get_user_by_id(user_id)
        if not user or not user.password_hash:
            raise ValueError("User not found or has no password")

        if not self.verify_password(data.current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        new_hash = self.hash_password(data.new_password)
        await execute_query(
            f"UPDATE users:`{user_id}` SET password_hash = $hash, updated_at = time::now()",
            {"hash": new_hash},
        )

        return True

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user and their settings.

        Args:
            user_id: User ID

        Returns:
            True if deleted
        """
        # Delete user settings
        await execute_query(
            "DELETE FROM user_settings WHERE user_id = $user_id",
            {"user_id": user_id},
        )

        # Delete user content links
        await execute_query(
            "DELETE FROM user_content WHERE user_id = $user_id",
            {"user_id": user_id},
        )

        # Delete user
        await execute_query(f"DELETE users:`{user_id}`")

        logger.info(f"Deleted user {user_id}")
        return True

    async def list_users(self) -> list[UserPublic]:
        """List all users (admin only).

        Returns:
            List of public user info
        """
        results = await execute_query(
            "SELECT * FROM users ORDER BY created_at DESC"
        )

        users = []
        for r in results:
            user = self._user_from_db(r)
            users.append(UserPublic.from_user(user))

        return users

    # =========================================================================
    # User Settings
    # =========================================================================

    async def create_user_settings(self, user_id: str) -> UserSettings:
        """Create default settings for a new user.

        Args:
            user_id: User ID

        Returns:
            Created settings
        """
        settings_id = str(uuid.uuid4())

        query = """
        INSERT INTO user_settings {
            id: $id,
            user_id: $user_id,
            api_keys: {},
            visible_models: [],
            preferences: {},
            created_at: time::now(),
            updated_at: time::now()
        };
        """

        await execute_query(query, {
            "id": settings_id,
            "user_id": user_id,
        })

        return UserSettings(
            id=settings_id,
            user_id=user_id,
        )

    async def get_user_settings(self, user_id: str) -> Optional[UserSettings]:
        """Get settings for a user.

        Args:
            user_id: User ID

        Returns:
            User settings or None
        """
        results = await execute_query(
            "SELECT * FROM user_settings WHERE user_id = $user_id",
            {"user_id": user_id},
        )

        if not results:
            return None

        r = results[0]
        settings_id = str(r.get("id", ""))
        if ":" in settings_id:
            settings_id = settings_id.split(":", 1)[1]

        return UserSettings(
            id=settings_id,
            user_id=r.get("user_id", user_id),
            api_keys=r.get("api_keys") or {},
            visible_models=r.get("visible_models") or [],
            preferences=r.get("preferences") or {},
            created_at=r.get("created_at", datetime.now()),
            updated_at=r.get("updated_at", datetime.now()),
        )

    async def update_user_settings(
        self,
        user_id: str,
        api_keys: Optional[dict[str, str]] = None,
        visible_models: Optional[list[str]] = None,
        preferences: Optional[dict] = None,
    ) -> Optional[UserSettings]:
        """Update user settings.

        Args:
            user_id: User ID
            api_keys: API keys to set (merged with existing)
            visible_models: Model IDs to show
            preferences: Preferences to set (merged with existing)

        Returns:
            Updated settings or None
        """
        settings = await self.get_user_settings(user_id)
        if not settings:
            settings = await self.create_user_settings(user_id)

        updates = ["updated_at = time::now()"]
        params = {"user_id": user_id}

        if api_keys is not None:
            # Merge with existing keys
            merged_keys = {**settings.api_keys, **api_keys}
            # Remove empty keys
            merged_keys = {k: v for k, v in merged_keys.items() if v}
            updates.append("api_keys = $api_keys")
            params["api_keys"] = merged_keys

        if visible_models is not None:
            updates.append("visible_models = $visible_models")
            params["visible_models"] = visible_models

        if preferences is not None:
            # Merge with existing preferences
            merged_prefs = {**settings.preferences, **preferences}
            updates.append("preferences = $preferences")
            params["preferences"] = merged_prefs

        set_clause = ", ".join(updates)
        await execute_query(
            f"UPDATE user_settings SET {set_clause} WHERE user_id = $user_id",
            params,
        )

        return await self.get_user_settings(user_id)

    # =========================================================================
    # Invites
    # =========================================================================

    async def create_invite(
        self,
        created_by: str,
        email: Optional[str] = None,
        expires_days: int = 7,
    ) -> Invite:
        """Create an invitation token.

        Args:
            created_by: User ID of the inviter
            email: Optional email to restrict invite to
            expires_days: Days until expiry

        Returns:
            Created invite
        """
        invite_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

        query = """
        INSERT INTO invites {
            id: $id,
            token: $token,
            email: $email,
            created_by: $created_by,
            expires_at: $expires_at,
            created_at: time::now()
        };
        """

        await execute_query(query, {
            "id": invite_id,
            "token": token,
            "email": email.lower() if email else None,
            "created_by": created_by,
            "expires_at": expires_at.isoformat(),
        })

        return Invite(
            id=invite_id,
            token=token,
            email=email.lower() if email else None,
            created_by=created_by,
            expires_at=expires_at,
        )

    async def validate_invite(self, token: str) -> Optional[Invite]:
        """Validate an invitation token.

        Args:
            token: Invite token

        Returns:
            Invite if valid, None otherwise
        """
        results = await execute_query(
            "SELECT * FROM invites WHERE token = $token",
            {"token": token},
        )

        if not results:
            return None

        r = results[0]
        invite_id = str(r.get("id", ""))
        if ":" in invite_id:
            invite_id = invite_id.split(":", 1)[1]

        expires_at = r.get("expires_at")
        if hasattr(expires_at, "isoformat"):
            pass
        elif isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        else:
            return None

        invite = Invite(
            id=invite_id,
            token=r.get("token", token),
            email=r.get("email"),
            created_by=r.get("created_by", ""),
            expires_at=expires_at,
            used_at=r.get("used_at"),
            used_by=r.get("used_by"),
        )

        if not invite.is_valid():
            return None

        return invite

    async def use_invite(self, token: str, user_id: str) -> bool:
        """Mark an invite as used.

        Args:
            token: Invite token
            user_id: User who used the invite

        Returns:
            True if successful
        """
        await execute_query(
            """
            UPDATE invites SET
                used_at = time::now(),
                used_by = $user_id
            WHERE token = $token
            """,
            {"token": token, "user_id": user_id},
        )
        return True

    # =========================================================================
    # Helpers
    # =========================================================================

    def _user_from_db(self, data: dict) -> User:
        """Convert database record to User model."""
        user_id = str(data.get("id", ""))
        if ":" in user_id:
            user_id = user_id.split(":", 1)[1]

        # Parse OAuth providers
        oauth_providers = []
        for p in data.get("oauth_providers") or []:
            if isinstance(p, dict):
                oauth_providers.append(OAuthProvider(**p))

        # Handle datetime conversion
        created_at = data.get("created_at", datetime.now())
        updated_at = data.get("updated_at", datetime.now())
        last_login_at = data.get("last_login_at")

        if hasattr(created_at, "isoformat"):
            pass  # Already datetime
        elif isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        if hasattr(updated_at, "isoformat"):
            pass
        elif isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        if last_login_at:
            if hasattr(last_login_at, "isoformat"):
                pass
            elif isinstance(last_login_at, str):
                last_login_at = datetime.fromisoformat(last_login_at.replace("Z", "+00:00"))

        return User(
            id=user_id,
            email=data.get("email", ""),
            password_hash=data.get("password_hash"),
            display_name=data.get("display_name", ""),
            role=data.get("role", UserRole.USER),
            oauth_providers=oauth_providers,
            email_verified=data.get("email_verified", False),
            created_at=created_at,
            updated_at=updated_at,
            last_login_at=last_login_at,
        )


# Singleton instance
_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get or create the auth service singleton."""
    global _service
    if _service is None:
        _service = AuthService()
    return _service
