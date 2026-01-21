"""
Authentication Middleware

FastAPI middleware for API key authentication and rate limiting.
"""

import os
import time
import hashlib
import logging
from typing import Optional, Dict, Callable, Awaitable
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.

    Limits requests per API key to prevent abuse.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit

        # Track requests per key
        self._minute_buckets: Dict[str, list] = defaultdict(list)
        self._hour_buckets: Dict[str, list] = defaultdict(list)

    def check_rate_limit(self, api_key: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is within rate limits.

        Returns:
            Tuple of (allowed, error_message)
        """
        now = time.time()

        # Clean old entries
        minute_ago = now - 60
        hour_ago = now - 3600

        self._minute_buckets[api_key] = [
            t for t in self._minute_buckets[api_key] if t > minute_ago
        ]
        self._hour_buckets[api_key] = [
            t for t in self._hour_buckets[api_key] if t > hour_ago
        ]

        # Check minute limit
        if len(self._minute_buckets[api_key]) >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"

        # Check hour limit
        if len(self._hour_buckets[api_key]) >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"

        # Check burst (requests in last second)
        second_ago = now - 1
        recent = [t for t in self._minute_buckets[api_key] if t > second_ago]
        if len(recent) >= self.burst_limit:
            return False, f"Burst limit exceeded: {self.burst_limit} requests per second"

        # Record request
        self._minute_buckets[api_key].append(now)
        self._hour_buckets[api_key].append(now)

        return True, None

    def get_remaining(self, api_key: str) -> Dict[str, int]:
        """Get remaining requests for the key."""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        minute_used = len([t for t in self._minute_buckets.get(api_key, []) if t > minute_ago])
        hour_used = len([t for t in self._hour_buckets.get(api_key, []) if t > hour_ago])

        return {
            "minute_remaining": self.requests_per_minute - minute_used,
            "hour_remaining": self.requests_per_hour - hour_used,
        }


class APIKeyAuth:
    """
    API Key Authentication.

    Validates API keys and manages permissions.
    """

    def __init__(self):
        # In production, this would come from a database
        self._valid_keys: Dict[str, Dict] = {}
        self._load_keys()

    def _load_keys(self):
        """Load API keys from environment or database."""
        # Load master key from environment
        master_key = os.getenv("AUTHORICY_MASTER_API_KEY")
        if master_key:
            self._valid_keys[self._hash_key(master_key)] = {
                "name": "Master Key",
                "permissions": ["*"],
                "rate_limit_multiplier": 10,  # 10x normal limits
                "created_at": datetime.now().isoformat(),
            }

        # Load additional keys from environment (comma-separated)
        additional_keys = os.getenv("AUTHORICY_API_KEYS", "")
        for key in additional_keys.split(","):
            key = key.strip()
            if key:
                self._valid_keys[self._hash_key(key)] = {
                    "name": f"Key-{key[:8]}",
                    "permissions": ["analyze", "reports"],
                    "rate_limit_multiplier": 1,
                    "created_at": datetime.now().isoformat(),
                }

    def _hash_key(self, key: str) -> str:
        """Hash API key for secure storage/comparison."""
        return hashlib.sha256(key.encode()).hexdigest()

    def validate_key(self, api_key: str) -> tuple[bool, Optional[Dict]]:
        """
        Validate an API key.

        Returns:
            Tuple of (valid, key_info)
        """
        if not api_key:
            return False, None

        key_hash = self._hash_key(api_key)
        key_info = self._valid_keys.get(key_hash)

        if key_info:
            return True, key_info

        return False, None

    def has_permission(self, key_info: Dict, permission: str) -> bool:
        """Check if key has a specific permission."""
        permissions = key_info.get("permissions", [])
        return "*" in permissions or permission in permissions

    def add_key(self, api_key: str, name: str, permissions: list) -> str:
        """Add a new API key."""
        key_hash = self._hash_key(api_key)
        self._valid_keys[key_hash] = {
            "name": name,
            "permissions": permissions,
            "rate_limit_multiplier": 1,
            "created_at": datetime.now().isoformat(),
        }
        return key_hash

    def revoke_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        key_hash = self._hash_key(api_key)
        if key_hash in self._valid_keys:
            del self._valid_keys[key_hash]
            return True
        return False


# Global instances
_auth = APIKeyAuth()
_rate_limiter = RateLimiter()


def auth_middleware(require_auth: bool = True, permission: Optional[str] = None):
    """
    Decorator for route authentication.

    Usage:
        @app.get("/analyze")
        @auth_middleware(permission="analyze")
        async def analyze_endpoint(request: Request):
            ...
    """
    def decorator(func: Callable[..., Awaitable]):
        async def wrapper(request: Request, *args, **kwargs):
            # Skip auth if not required (e.g., health checks)
            if not require_auth:
                return await func(request, *args, **kwargs)

            # Get API key from header
            api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")

            if not api_key:
                raise HTTPException(
                    status_code=401,
                    detail="Missing API key. Include X-API-Key header."
                )

            # Validate key
            valid, key_info = _auth.validate_key(api_key)

            if not valid:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key."
                )

            # Check permission
            if permission and not _auth.has_permission(key_info, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"API key lacks required permission: {permission}"
                )

            # Check rate limit
            multiplier = key_info.get("rate_limit_multiplier", 1)
            _rate_limiter.requests_per_minute = 60 * multiplier
            _rate_limiter.requests_per_hour = 1000 * multiplier

            allowed, error = _rate_limiter.check_rate_limit(api_key)

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=error
                )

            # Add key info to request state for downstream use
            request.state.api_key_info = key_info

            return await func(request, *args, **kwargs)

        return wrapper
    return decorator


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware for global auth checking.

    Applies to all routes except those in EXEMPT_PATHS.
    """

    EXEMPT_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Get API key
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")

        # Allow if no auth configured (development mode)
        if not os.getenv("AUTHORICY_REQUIRE_AUTH", "").lower() in ("true", "1", "yes"):
            return await call_next(request)

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key. Include X-API-Key header."}
            )

        # Validate
        valid, key_info = _auth.validate_key(api_key)

        if not valid:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key."}
            )

        # Rate limit
        allowed, error = _rate_limiter.check_rate_limit(api_key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": error}
            )

        # Add rate limit headers
        remaining = _rate_limiter.get_remaining(api_key)

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute_remaining"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour_remaining"])

        return response
