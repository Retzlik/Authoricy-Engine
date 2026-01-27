"""
FastAPI Authentication Dependencies

Provides dependency injection for authentication and authorization.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import Domain
from src.auth.models import User, UserRole
from src.auth.jwt import verify_supabase_token, JWTError
from src.auth.sync import sync_user_from_supabase
from src.auth.config import get_auth_config

logger = logging.getLogger(__name__)

# HTTP Bearer token extraction
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user.

    Validates JWT, syncs user to local DB, returns User object.

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If user is disabled
    """
    config = get_auth_config()

    # If auth is disabled (local dev), return a mock user
    if not config.auth_enabled:
        return _get_dev_user(db)

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Verify the JWT token
        payload = verify_supabase_token(credentials.credentials)

        # Sync user to local database
        user = sync_user_from_supabase(db, payload)

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        return user

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.

    Use this for endpoints that support both authenticated and anonymous access.
    """
    config = get_auth_config()

    if not config.auth_enabled:
        return _get_dev_user(db)

    if not credentials:
        return None

    try:
        payload = verify_supabase_token(credentials.credentials)
        user = sync_user_from_supabase(db, payload)
        return user if user.is_active else None
    except JWTError:
        return None


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require the current user to be an admin.

    Raises:
        HTTPException 403: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


class DomainAccessChecker:
    """
    Dependency class for checking domain ownership.

    Usage:
        @router.get("/domains/{domain_id}")
        def get_domain(
            domain_id: UUID,
            domain: Domain = Depends(get_owned_domain)
        ):
            # domain is guaranteed to be owned by current user or user is admin
            ...
    """

    def __init__(self, allow_admin_access: bool = True):
        self.allow_admin_access = allow_admin_access

    async def __call__(
        self,
        domain_id: UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Domain:
        """Check domain ownership and return domain."""
        domain = db.query(Domain).filter(Domain.id == domain_id).first()

        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Domain not found",
            )

        # Admin can access any domain
        if self.allow_admin_access and current_user.is_admin:
            return domain

        # Regular user must own the domain
        if domain.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this domain",
            )

        return domain


# Pre-configured instances
get_owned_domain = DomainAccessChecker(allow_admin_access=True)
require_domain_access = DomainAccessChecker(allow_admin_access=True)


def _get_dev_user(db: Session) -> User:
    """
    Get or create a development user when auth is disabled.

    This allows local development without Supabase.
    """
    from uuid import uuid4

    dev_email = "dev@authoricy.local"
    user = db.query(User).filter(User.email == dev_email).first()

    if not user:
        user = User(
            id=uuid4(),
            email=dev_email,
            full_name="Development User",
            role=UserRole.ADMIN,  # Dev user gets admin for testing
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
