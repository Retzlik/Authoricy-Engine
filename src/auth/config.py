"""
Authentication Configuration

Settings for Supabase JWT validation and auth behavior.
"""

import os
from typing import Optional
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    """Authentication configuration loaded from environment."""

    # Supabase Configuration
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""

    # JWT Settings
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "authenticated"

    # Auth behavior
    auth_enabled: bool = True  # Set to False for local dev without auth
    allow_unauthenticated_health: bool = True  # Health endpoints don't require auth

    # Admin configuration
    admin_emails: list[str] = []  # Emails that are auto-promoted to admin

    @field_validator('admin_emails', mode='before')
    @classmethod
    def parse_admin_emails(cls, v):
        """Parse comma-separated string into list of emails."""
        if isinstance(v, str):
            # Handle comma-separated string from env var
            return [email.strip() for email in v.split(',') if email.strip()]
        return v or []

    class Config:
        env_prefix = ""
        extra = "ignore"

    @property
    def supabase_project_ref(self) -> Optional[str]:
        """Extract project reference from Supabase URL."""
        if not self.supabase_url:
            return None
        # https://abcdefg.supabase.co -> abcdefg
        try:
            return self.supabase_url.replace("https://", "").split(".")[0]
        except:
            return None

    @property
    def is_configured(self) -> bool:
        """Check if auth is properly configured."""
        return bool(
            self.supabase_url and
            self.supabase_jwt_secret
        )


@lru_cache()
def get_auth_config() -> AuthConfig:
    """Get cached auth configuration."""
    return AuthConfig(
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        supabase_jwt_secret=os.getenv("SUPABASE_JWT_SECRET", ""),
        auth_enabled=os.getenv("AUTH_ENABLED", "true").lower() == "true",
        admin_emails=os.getenv("ADMIN_EMAILS", "").split(",") if os.getenv("ADMIN_EMAILS") else [],
    )
