"""
Authentication and Authorization Module

Provides two authentication methods:
1. Supabase JWT Auth - For frontend user authentication (users, admins)
2. API Key Auth - For programmatic/M2M access (backward compatible)

Supabase Integration:
- Users sign up/login via Supabase Auth
- JWTs are validated against Supabase JWT secret
- Users are synced to local PostgreSQL on first access
- Role-based access control (user, admin)
- Domain ownership enforcement

API Key Auth (Legacy/M2M):
- API keys for machine-to-machine communication
- Rate limiting per key
- Permission-based access control

Usage:
    # Supabase JWT auth (recommended for frontend)
    @router.get("/domains")
    def list_domains(current_user: User = Depends(get_current_user)):
        ...

    # Admin-only endpoints
    @router.get("/admin/users")
    def list_users(admin: User = Depends(require_admin)):
        ...

    # Domain ownership check
    @router.get("/domains/{domain_id}")
    def get_domain(domain: Domain = Depends(get_owned_domain)):
        ...

    # API key auth (for programmatic access)
    @auth_middleware(permission="analyze")
    async def analyze_endpoint(request: Request):
        ...
"""

# Legacy API Key authentication (backward compatible)
from .middleware import APIKeyAuth, RateLimiter, auth_middleware
from .keys import APIKeyManager, APIKey
from .usage import UsageTracker, UsageRecord

# New Supabase JWT authentication
from .config import AuthConfig, get_auth_config
from .jwt import verify_supabase_token, decode_token_unverified, JWTError
from .models import User, UserRole
from .sync import sync_user_from_supabase, get_user_by_id, get_user_by_email
from .dependencies import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    get_owned_domain,
    require_domain_access,
)

__all__ = [
    # Legacy API Key auth
    "APIKeyAuth",
    "RateLimiter",
    "auth_middleware",
    "APIKeyManager",
    "APIKey",
    "UsageTracker",
    "UsageRecord",
    # Supabase JWT auth config
    "AuthConfig",
    "get_auth_config",
    # JWT validation
    "verify_supabase_token",
    "decode_token_unverified",
    "JWTError",
    # User model
    "User",
    "UserRole",
    # User sync
    "sync_user_from_supabase",
    "get_user_by_id",
    "get_user_by_email",
    # FastAPI dependencies
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "get_owned_domain",
    "require_domain_access",
]
