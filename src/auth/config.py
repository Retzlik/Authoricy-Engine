"""
Authentication Configuration

Settings for Supabase JWT validation and auth behavior.
"""

import os
from typing import Optional
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


def parse_admin_emails_from_env() -> list[str]:
    """Parse ADMIN_EMAILS env var as comma-separated string."""
    raw = os.getenv("ADMIN_EMAILS", "")
    if not raw:
        return []
    return [email.strip() for email in raw.split(",") if email.strip()]


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
    # NOTE: validation_alias prevents BaseSettings from auto-loading ADMIN_EMAILS env var
    # (which would fail because it tries to JSON-parse a comma-separated string).
    # The value is parsed manually in get_auth_config() using parse_admin_emails_from_env().
    admin_emails: list[str] = Field(
        default_factory=list,
        validation_alias="__ADMIN_EMAILS_DO_NOT_AUTO_LOAD__"
    )

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
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        auth_enabled=os.getenv("AUTH_ENABLED", "true").lower() == "true",
        admin_emails=parse_admin_emails_from_env(),
    )
