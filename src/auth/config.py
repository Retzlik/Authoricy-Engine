"""
Authentication Configuration

Settings for Supabase JWT validation and auth behavior.
"""

import os
from typing import Annotated, Optional
from functools import lru_cache
from pydantic import BeforeValidator
from pydantic_settings import BaseSettings


def parse_comma_separated_emails(v) -> list[str]:
    """Parse comma-separated string into list of emails."""
    if v is None:
        return []
    if isinstance(v, str):
        return [email.strip() for email in v.split(',') if email.strip()]
    if isinstance(v, list):
        return v
    return []


# Custom type that handles comma-separated strings from env vars
EmailList = Annotated[list[str], BeforeValidator(parse_comma_separated_emails)]


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

    # Admin configuration - uses custom type to parse comma-separated env var
    admin_emails: EmailList = []

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
