"""
JWT Token Validation for Supabase Auth

Validates JWTs issued by Supabase using the project's JWT secret.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import jwt
from jwt import PyJWTError

from src.auth.config import get_auth_config

logger = logging.getLogger(__name__)


class JWTError(Exception):
    """Custom JWT validation error."""
    pass


def verify_supabase_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a Supabase JWT token.

    Args:
        token: The JWT token from the Authorization header

    Returns:
        Decoded token payload containing user info

    Raises:
        JWTError: If token is invalid, expired, or malformed
    """
    config = get_auth_config()

    if not config.supabase_jwt_secret:
        raise JWTError("Supabase JWT secret not configured")

    try:
        # Decode and verify the token
        payload = jwt.decode(
            token,
            config.supabase_jwt_secret,
            algorithms=[config.jwt_algorithm],
            audience=config.jwt_audience,
        )

        # Check expiration (jwt library does this, but let's be explicit)
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise JWTError("Token has expired")

        # Validate required claims
        if not payload.get("sub"):
            raise JWTError("Token missing 'sub' claim (user ID)")

        return payload

    except jwt.ExpiredSignatureError:
        raise JWTError("Token has expired")
    except jwt.InvalidAudienceError:
        raise JWTError("Invalid token audience")
    except jwt.InvalidSignatureError:
        raise JWTError("Invalid token signature")
    except jwt.DecodeError as e:
        raise JWTError(f"Token decode error: {str(e)}")
    except PyJWTError as e:
        raise JWTError(f"Token validation error: {str(e)}")


def decode_token_unverified(token: str) -> Dict[str, Any]:
    """
    Decode a token without verification (for debugging only).

    WARNING: Never use this for authentication decisions.
    """
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        raise JWTError(f"Failed to decode token: {str(e)}")


def extract_user_info(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract user information from a verified JWT payload.

    Supabase JWT payload structure:
    {
        "sub": "user-uuid",
        "email": "user@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "app_metadata": {...},
        "user_metadata": {
            "full_name": "John Doe",
            "avatar_url": "https://..."
        },
        "exp": 1234567890,
        "iat": 1234567800
    }
    """
    user_metadata = payload.get("user_metadata", {})
    app_metadata = payload.get("app_metadata", {})

    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "full_name": user_metadata.get("full_name") or user_metadata.get("name"),
        "avatar_url": user_metadata.get("avatar_url") or user_metadata.get("picture"),
        "provider": app_metadata.get("provider", "email"),
        "role": payload.get("role", "authenticated"),
    }
