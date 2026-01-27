"""
User Synchronization from Supabase

Syncs user data from Supabase JWT to local database on first access.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.auth.models import User, UserRole
from src.auth.config import get_auth_config
from src.auth.jwt import extract_user_info

logger = logging.getLogger(__name__)


def sync_user_from_supabase(
    db: Session,
    jwt_payload: Dict[str, Any],
) -> User:
    """
    Sync user from Supabase JWT payload to local database.

    Creates user on first access, updates on subsequent accesses.

    Args:
        db: Database session
        jwt_payload: Verified JWT payload from Supabase

    Returns:
        Local User record (created or updated)
    """
    user_info = extract_user_info(jwt_payload)
    user_id = UUID(user_info["id"])

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()

    config = get_auth_config()

    if user is None:
        # Create new user
        logger.info(f"Creating new user: {user_info['email']}")

        # Check if email should be auto-promoted to admin
        role = UserRole.USER
        if user_info["email"] in config.admin_emails:
            role = UserRole.ADMIN
            logger.info(f"Auto-promoting {user_info['email']} to admin")

        user = User(
            id=user_id,
            email=user_info["email"],
            full_name=user_info.get("full_name"),
            avatar_url=user_info.get("avatar_url"),
            provider=user_info.get("provider"),
            role=role,
            is_active=True,
            last_sign_in_at=datetime.utcnow(),
            synced_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    else:
        # Update existing user
        user.email = user_info["email"]
        user.full_name = user_info.get("full_name") or user.full_name
        user.avatar_url = user_info.get("avatar_url") or user.avatar_url
        user.last_sign_in_at = datetime.utcnow()
        user.synced_at = datetime.utcnow()

        # Check for admin promotion (email added to ADMIN_EMAILS)
        if user_info["email"] in config.admin_emails and user.role != UserRole.ADMIN:
            logger.info(f"Promoting {user_info['email']} to admin")
            user.role = UserRole.ADMIN

        db.commit()
        db.refresh(user)

    return user


def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()
