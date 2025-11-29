"""Authentication API endpoints.

Endpoints:
- POST /auth/register - Register new user
- POST /auth/login - Login and get JWT token
- GET /auth/me - Get current user info
- PUT /auth/me - Update current user profile
- POST /auth/change-password - Change password
- GET /auth/check - Check if registration is open

Admin endpoints:
- GET /auth/users - List all users
- DELETE /auth/users/{id} - Delete a user
- POST /auth/invites - Create invite
- GET /auth/invites - List invites
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from compose.lib.config_manager import config
from compose.services.auth import (
    AuthService,
    PasswordChange,
    TokenResponse,
    User,
    UserCreate,
    UserPublic,
    UserRole,
    UserUpdate,
    get_auth_service,
)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


# =============================================================================
# Dependencies
# =============================================================================


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency to get current authenticated user.

    Raises:
        HTTPException: If not authenticated or token invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth.verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth.get_user_by_id(payload.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth: AuthService = Depends(get_auth_service),
) -> Optional[User]:
    """Dependency to get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    payload = auth.verify_token(credentials.credentials)
    if not payload:
        return None

    return await auth.get_user_by_id(payload.sub)


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency to require admin role.

    Raises:
        HTTPException: If user is not an admin
    """
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# =============================================================================
# Request/Response Models
# =============================================================================


class LoginRequest(BaseModel):
    """Login request body."""
    email: str
    password: str


class RegisterRequest(BaseModel):
    """Registration request body."""
    email: str
    password: str
    display_name: Optional[str] = None
    invite_token: Optional[str] = None


class RegistrationStatus(BaseModel):
    """Registration status response."""
    is_open: bool
    requires_invite: bool
    is_first_user: bool


class InviteCreateRequest(BaseModel):
    """Invite creation request."""
    email: Optional[str] = None
    expires_days: int = 7


class InviteResponse(BaseModel):
    """Invite response."""
    id: str
    token: str
    email: Optional[str]
    expires_at: str
    used: bool


# =============================================================================
# Public Endpoints
# =============================================================================


@router.get("/check", response_model=RegistrationStatus)
async def check_registration(
    auth: AuthService = Depends(get_auth_service),
):
    """Check registration status.

    Returns whether registration is open and if this would be the first user.
    """
    is_first = await auth.is_first_user()
    is_open = is_first or config.get("REGISTRATION_OPEN", False)

    return RegistrationStatus(
        is_open=is_open,
        requires_invite=not is_open and not is_first,
        is_first_user=is_first,
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    data: RegisterRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Register a new user.

    First user becomes admin. After that, registration requires:
    - REGISTRATION_OPEN=true, or
    - Valid invite token
    """
    is_first = await auth.is_first_user()
    is_open = config.get("REGISTRATION_OPEN", False)

    # Check if registration is allowed
    if not is_first and not is_open:
        # Need invite token
        if not data.invite_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration requires an invite",
            )

        invite = await auth.validate_invite(data.invite_token)
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invite",
            )

        # Check email restriction
        if invite.email and invite.email.lower() != data.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invite is for a different email",
            )

    # Create user
    try:
        user = await auth.create_user(
            UserCreate(
                email=data.email,
                password=data.password,
                display_name=data.display_name,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Mark invite as used
    if data.invite_token:
        await auth.use_invite(data.invite_token, user.id)

    # Return token
    token, expires_in = auth.create_access_token(user)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserPublic.from_user(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
):
    """Login with email and password.

    Returns JWT token on success.
    """
    result = await auth.login(data.email, data.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return result


# =============================================================================
# Authenticated User Endpoints
# =============================================================================


@router.get("/me", response_model=UserPublic)
async def get_me(
    user: User = Depends(get_current_user),
):
    """Get current user info."""
    return UserPublic.from_user(user)


@router.put("/me", response_model=UserPublic)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
):
    """Update current user profile."""
    try:
        updated = await auth.update_user(user.id, data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserPublic.from_user(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
):
    """Change current user's password."""
    try:
        await auth.change_password(user.id, data)
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# =============================================================================
# Admin Endpoints
# =============================================================================


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    _: User = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
):
    """List all users (admin only)."""
    return await auth.list_users()


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
):
    """Delete a user (admin only).

    Cannot delete yourself.
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    await auth.delete_user(user_id)
    return {"message": "User deleted"}


@router.post("/invites", response_model=InviteResponse)
async def create_invite(
    data: InviteCreateRequest,
    user: User = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
):
    """Create an invitation (admin only)."""
    invite = await auth.create_invite(
        created_by=user.id,
        email=data.email,
        expires_days=data.expires_days,
    )

    return InviteResponse(
        id=invite.id or "",
        token=invite.token,
        email=invite.email,
        expires_at=invite.expires_at.isoformat(),
        used=invite.used_at is not None,
    )


@router.get("/invites", response_model=list[InviteResponse])
async def list_invites(
    _: User = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
):
    """List all invites (admin only)."""
    from compose.services.surrealdb.driver import execute_query

    results = await execute_query(
        "SELECT * FROM invites ORDER BY created_at DESC"
    )

    invites = []
    for r in results:
        invite_id = str(r.get("id", ""))
        if ":" in invite_id:
            invite_id = invite_id.split(":", 1)[1]

        expires_at = r.get("expires_at", "")
        if hasattr(expires_at, "isoformat"):
            expires_at = expires_at.isoformat()

        invites.append(InviteResponse(
            id=invite_id,
            token=r.get("token", ""),
            email=r.get("email"),
            expires_at=expires_at,
            used=r.get("used_at") is not None,
        ))

    return invites
