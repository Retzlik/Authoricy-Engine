"""
User Management API

Provides endpoints for user profile and admin user management.

Endpoints:
- GET /api/users/me - Get current user profile
- PATCH /api/users/me - Update current user profile
- GET /api/users - List all users (admin only)
- GET /api/users/{user_id} - Get user by ID (admin only)
- PATCH /api/users/{user_id}/role - Update user role (admin only)
- DELETE /api/users/{user_id} - Disable user (admin only)
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import Domain
from src.auth.models import User, UserRole
from src.auth.dependencies import get_current_user, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],  # All endpoints require authentication
)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class UserResponse(BaseModel):
    """User profile response."""
    id: UUID
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    is_active: bool
    provider: Optional[str]
    domain_count: int = 0
    created_at: datetime
    last_sign_in_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


class UpdateProfileRequest(BaseModel):
    """Request to update user profile."""
    full_name: Optional[str] = Field(None, max_length=255)


class UpdateRoleRequest(BaseModel):
    """Request to update user role (admin only)."""
    role: str = Field(..., pattern="^(user|admin)$")


# =============================================================================
# USER PROFILE ENDPOINTS
# =============================================================================

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current authenticated user's profile.

    Returns user info including role and domain count.
    """
    domain_count = db.query(Domain).filter(Domain.user_id == current_user.id).count()

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        role=current_user.role.value,
        is_active=current_user.is_active,
        provider=current_user.provider,
        domain_count=domain_count,
        created_at=current_user.created_at,
        last_sign_in_at=current_user.last_sign_in_at,
    )


@router.patch("/me", response_model=UserResponse)
def update_current_user_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's profile.

    Only allows updating non-sensitive fields like full_name.
    Email and role changes require admin access.
    """
    if request.full_name is not None:
        current_user.full_name = request.full_name

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    domain_count = db.query(Domain).filter(Domain.user_id == current_user.id).count()

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        role=current_user.role.value,
        is_active=current_user.is_active,
        provider=current_user.provider,
        domain_count=domain_count,
        created_at=current_user.created_at,
        last_sign_in_at=current_user.last_sign_in_at,
    )


# =============================================================================
# ADMIN USER MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None, pattern="^(user|admin)$"),
    search: Optional[str] = Query(None, max_length=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all users (admin only).

    Supports filtering by role and searching by email/name.
    """
    query = db.query(User)

    # Filter by role
    if role:
        query = query.filter(User.role == UserRole(role))

    # Search by email or name
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )

    # Get total count
    total = query.count()

    # Paginate
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Build response with domain counts
    user_responses = []
    for user in users:
        domain_count = db.query(Domain).filter(Domain.user_id == user.id).count()
        user_responses.append(UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            role=user.role.value,
            is_active=user.is_active,
            provider=user.provider,
            domain_count=domain_count,
            created_at=user.created_at,
            last_sign_in_at=user.last_sign_in_at,
        ))

    return UserListResponse(
        users=user_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get a specific user by ID (admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    domain_count = db.query(Domain).filter(Domain.user_id == user.id).count()

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=user.role.value,
        is_active=user.is_active,
        provider=user.provider,
        domain_count=domain_count,
        created_at=user.created_at,
        last_sign_in_at=user.last_sign_in_at,
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: UUID,
    request: UpdateRoleRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update a user's role (admin only).

    Admins cannot demote themselves to prevent lockout.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-demotion
    if user.id == admin.id and request.role == "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself. Have another admin change your role.",
        )

    user.role = UserRole(request.role)
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    logger.info(f"Admin {admin.email} changed user {user.email} role to {request.role}")

    domain_count = db.query(Domain).filter(Domain.user_id == user.id).count()

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=user.role.value,
        is_active=user.is_active,
        provider=user.provider,
        domain_count=domain_count,
        created_at=user.created_at,
        last_sign_in_at=user.last_sign_in_at,
    )


@router.delete("/{user_id}")
def disable_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Disable a user account (admin only).

    This doesn't delete the user, just prevents them from accessing the API.
    The Supabase account remains active - disable there too for full lockout.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-disable
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account.",
        )

    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Admin {admin.email} disabled user {user.email}")

    return {"status": "disabled", "user_id": str(user_id)}


@router.post("/{user_id}/enable")
def enable_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Re-enable a disabled user account (admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Admin {admin.email} enabled user {user.email}")

    return {"status": "enabled", "user_id": str(user_id)}
