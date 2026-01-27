"""
JWT Token Validation for Supabase Auth

Validates JWTs issued by Supabase using the project's JWT secret or JWKS.
Supports both symmetric (HS256) and asymmetric (ES256, RS256) algorithms.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from functools import lru_cache

import jwt
from jwt import PyJWTError, PyJWKClient

from src.auth.config import get_auth_config

logger = logging.getLogger(__name__)

# Asymmetric algorithms that require public key (JWKS) verification
ASYMMETRIC_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "PS256", "PS384", "PS512"}


class JWTError(Exception):
    """Custom JWT validation error."""
    pass


@lru_cache(maxsize=1)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Get cached JWKS client for fetching public keys."""
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


def get_verification_key(token: str, config) -> Any:
    """
    Get the appropriate verification key based on algorithm.

    - For symmetric algorithms (HS256): Use the JWT secret directly
    - For asymmetric algorithms (ES256, RS256): Fetch public key from JWKS
    """
    if config.jwt_algorithm in ASYMMETRIC_ALGORITHMS:
        # Asymmetric: need to fetch public key from Supabase JWKS
        if not config.supabase_url:
            raise JWTError(
                f"SUPABASE_URL required for {config.jwt_algorithm} algorithm. "
                "Set SUPABASE_URL environment variable."
            )

        # Extract project ref from URL: https://abc123.supabase.co -> abc123
        project_ref = config.supabase_project_ref
        if not project_ref:
            raise JWTError("Could not extract project reference from SUPABASE_URL")

        jwks_url = f"https://{project_ref}.supabase.co/auth/v1/.well-known/jwks.json"

        try:
            jwks_client = get_jwks_client(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            return signing_key.key
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
            raise JWTError(f"Failed to fetch public key from Supabase: {str(e)}")
    else:
        # Symmetric: use JWT secret directly
        if not config.supabase_jwt_secret:
            raise JWTError("SUPABASE_JWT_SECRET not configured")
        return config.supabase_jwt_secret


def verify_supabase_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a Supabase JWT token.

    Supports both symmetric (HS256) and asymmetric (ES256, RS256) algorithms.
    - HS256: Uses SUPABASE_JWT_SECRET for verification
    - ES256/RS256: Fetches public key from Supabase JWKS endpoint

    Args:
        token: The JWT token from the Authorization header

    Returns:
        Decoded token payload containing user info

    Raises:
        JWTError: If token is invalid, expired, or malformed
    """
    config = get_auth_config()

    try:
        # Get token header to check algorithm
        try:
            unverified_header = jwt.get_unverified_header(token)
            token_alg = unverified_header.get("alg", "unknown")
            if token_alg != config.jwt_algorithm:
                logger.warning(
                    f"JWT algorithm mismatch: token uses '{token_alg}', "
                    f"config expects '{config.jwt_algorithm}'. "
                    f"Set JWT_ALGORITHM env var if needed."
                )
        except Exception:
            pass  # Don't fail on header inspection

        # Get appropriate verification key (secret or public key)
        verification_key = get_verification_key(token, config)

        # Decode and verify the token
        payload = jwt.decode(
            token,
            verification_key,
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

    except jwt.exceptions.InvalidAlgorithmError as e:
        # Algorithm mismatch - provide helpful error message
        try:
            header = jwt.get_unverified_header(token)
            token_alg = header.get("alg", "unknown")
        except Exception:
            token_alg = "unknown"
        raise JWTError(
            f"JWT algorithm mismatch: token uses '{token_alg}', "
            f"server expects '{config.jwt_algorithm}'. "
            f"Set JWT_ALGORITHM={token_alg} in environment variables."
        )
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
