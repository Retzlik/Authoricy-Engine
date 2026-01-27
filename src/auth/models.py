"""
Authentication Models

User model and related enums for Authoricy authentication.
These are added to the main database alongside existing models.
"""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Boolean, DateTime, Enum, Index, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models import Base


class UserRole(enum.Enum):
    """User role for access control."""
    USER = "user"      # Regular user - sees only their own domains
    ADMIN = "admin"    # Admin - sees all domains, can manage users


class User(Base):
    """
    Local user record synced from Supabase Auth.

    This table mirrors essential user data from Supabase for:
    - Fast lookups without external API calls
    - Foreign key relationships with domains
    - Role-based access control
    - Audit trails

    The id matches the Supabase auth.users.id (UUID).
    """
    __tablename__ = "users"

    # ID matches Supabase auth.users.id
    id = Column(UUID(as_uuid=True), primary_key=True)

    # Basic info (synced from Supabase)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(2000))

    # Role (managed locally, not in Supabase)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    provider = Column(String(50))  # email, google, github, etc.

    # Last sync with Supabase
    last_sign_in_at = Column(DateTime)
    synced_at = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    domains = relationship("Domain", back_populates="user", foreign_keys="Domain.user_id")

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_role", "role"),
    )

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"
