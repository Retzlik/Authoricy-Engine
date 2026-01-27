"""
Authentication Tests

Tests for the Supabase JWT authentication system.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch

import jwt

from src.auth.config import AuthConfig, get_auth_config
from src.auth.jwt import verify_supabase_token, JWTError, extract_user_info
from src.auth.models import User, UserRole
from src.auth.sync import sync_user_from_supabase


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def auth_config():
    """Create test auth config."""
    return AuthConfig(
        supabase_url="https://test.supabase.co",
        supabase_anon_key="test-anon-key",
        supabase_jwt_secret="super-secret-jwt-key-for-testing",
        jwt_algorithm="HS256",
        jwt_audience="authenticated",
        auth_enabled=True,
        admin_emails=["admin@test.com"],
    )


@pytest.fixture
def valid_jwt_payload():
    """Create valid JWT payload."""
    return {
        "sub": str(uuid4()),
        "email": "user@test.com",
        "role": "authenticated",
        "aud": "authenticated",
        "user_metadata": {
            "full_name": "Test User",
            "avatar_url": "https://example.com/avatar.png",
        },
        "app_metadata": {
            "provider": "email",
        },
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }


@pytest.fixture
def create_test_token(auth_config):
    """Factory to create test JWT tokens."""
    def _create(payload: dict) -> str:
        return jwt.encode(
            payload,
            auth_config.supabase_jwt_secret,
            algorithm=auth_config.jwt_algorithm,
        )
    return _create


# =============================================================================
# JWT VALIDATION TESTS
# =============================================================================

class TestJWTValidation:
    """Tests for JWT token validation."""

    def test_valid_token(self, auth_config, valid_jwt_payload, create_test_token):
        """Test that a valid token is accepted."""
        with patch("src.auth.jwt.get_auth_config", return_value=auth_config):
            token = create_test_token(valid_jwt_payload)
            payload = verify_supabase_token(token)

            assert payload["sub"] == valid_jwt_payload["sub"]
            assert payload["email"] == valid_jwt_payload["email"]

    def test_expired_token(self, auth_config, valid_jwt_payload, create_test_token):
        """Test that expired tokens are rejected."""
        valid_jwt_payload["exp"] = int((datetime.utcnow() - timedelta(hours=1)).timestamp())

        with patch("src.auth.jwt.get_auth_config", return_value=auth_config):
            token = create_test_token(valid_jwt_payload)

            with pytest.raises(JWTError, match="expired"):
                verify_supabase_token(token)

    def test_invalid_signature(self, auth_config, valid_jwt_payload):
        """Test that tokens with invalid signatures are rejected."""
        # Create token with wrong secret
        token = jwt.encode(
            valid_jwt_payload,
            "wrong-secret",
            algorithm="HS256",
        )

        with patch("src.auth.jwt.get_auth_config", return_value=auth_config):
            with pytest.raises(JWTError, match="signature"):
                verify_supabase_token(token)

    def test_missing_sub_claim(self, auth_config, valid_jwt_payload, create_test_token):
        """Test that tokens without 'sub' claim are rejected."""
        del valid_jwt_payload["sub"]

        with patch("src.auth.jwt.get_auth_config", return_value=auth_config):
            token = create_test_token(valid_jwt_payload)

            with pytest.raises(JWTError, match="sub"):
                verify_supabase_token(token)

    def test_invalid_audience(self, auth_config, valid_jwt_payload, create_test_token):
        """Test that tokens with wrong audience are rejected."""
        valid_jwt_payload["aud"] = "wrong-audience"

        with patch("src.auth.jwt.get_auth_config", return_value=auth_config):
            token = create_test_token(valid_jwt_payload)

            with pytest.raises(JWTError, match="audience"):
                verify_supabase_token(token)

    def test_no_jwt_secret_configured(self, valid_jwt_payload, create_test_token):
        """Test error when JWT secret not configured."""
        config = AuthConfig(supabase_jwt_secret="")

        with patch("src.auth.jwt.get_auth_config", return_value=config):
            with pytest.raises(JWTError, match="not configured"):
                verify_supabase_token("any-token")


class TestExtractUserInfo:
    """Tests for extracting user info from JWT payload."""

    def test_extract_full_user_info(self, valid_jwt_payload):
        """Test extracting complete user info."""
        info = extract_user_info(valid_jwt_payload)

        assert info["id"] == valid_jwt_payload["sub"]
        assert info["email"] == valid_jwt_payload["email"]
        assert info["full_name"] == "Test User"
        assert info["avatar_url"] == "https://example.com/avatar.png"
        assert info["provider"] == "email"

    def test_extract_minimal_user_info(self):
        """Test extracting user info with minimal claims."""
        payload = {
            "sub": "user-123",
            "email": "minimal@test.com",
        }
        info = extract_user_info(payload)

        assert info["id"] == "user-123"
        assert info["email"] == "minimal@test.com"
        assert info["full_name"] is None
        assert info["avatar_url"] is None

    def test_google_oauth_metadata(self):
        """Test extracting user info from Google OAuth payload."""
        payload = {
            "sub": "user-123",
            "email": "user@gmail.com",
            "user_metadata": {
                "name": "Google User",  # Google uses 'name' not 'full_name'
                "picture": "https://googleusercontent.com/avatar.png",  # 'picture' not 'avatar_url'
            },
            "app_metadata": {
                "provider": "google",
            },
        }
        info = extract_user_info(payload)

        assert info["full_name"] == "Google User"
        assert info["avatar_url"] == "https://googleusercontent.com/avatar.png"
        assert info["provider"] == "google"


# =============================================================================
# USER SYNC TESTS
# =============================================================================

class TestUserSync:
    """Tests for user synchronization."""

    def test_sync_creates_new_user(self, valid_jwt_payload):
        """Test that a new user is created on first sync."""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("src.auth.sync.get_auth_config") as mock_config:
            mock_config.return_value.admin_emails = []

            user = sync_user_from_supabase(mock_db, valid_jwt_payload)

            # Should have created a new user
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called()

    def test_sync_updates_existing_user(self, valid_jwt_payload):
        """Test that existing user is updated on subsequent sync."""
        existing_user = User(
            id=uuid4(),
            email="old@test.com",
            role=UserRole.USER,
            is_active=True,
        )

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        with patch("src.auth.sync.get_auth_config") as mock_config:
            mock_config.return_value.admin_emails = []

            user = sync_user_from_supabase(mock_db, valid_jwt_payload)

            # Should update email
            assert user.email == valid_jwt_payload["email"]
            mock_db.commit.assert_called()
            # Should NOT add a new user
            mock_db.add.assert_not_called()

    def test_sync_auto_promotes_admin(self, valid_jwt_payload):
        """Test that admin emails are auto-promoted."""
        valid_jwt_payload["email"] = "admin@test.com"

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("src.auth.sync.get_auth_config") as mock_config:
            mock_config.return_value.admin_emails = ["admin@test.com"]

            user = sync_user_from_supabase(mock_db, valid_jwt_payload)

            # Check that the added user has admin role
            added_user = mock_db.add.call_args[0][0]
            assert added_user.role == UserRole.ADMIN


# =============================================================================
# USER MODEL TESTS
# =============================================================================

class TestUserModel:
    """Tests for User model."""

    def test_is_admin_true(self):
        """Test is_admin returns True for admin users."""
        user = User(
            id=uuid4(),
            email="admin@test.com",
            role=UserRole.ADMIN,
            is_active=True,
        )
        assert user.is_admin is True

    def test_is_admin_false(self):
        """Test is_admin returns False for regular users."""
        user = User(
            id=uuid4(),
            email="user@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        assert user.is_admin is False

    def test_user_repr(self):
        """Test User string representation."""
        user = User(
            id=uuid4(),
            email="user@test.com",
            role=UserRole.USER,
            is_active=True,
        )
        assert "user@test.com" in repr(user)
        assert "user" in repr(user)


# =============================================================================
# AUTH CONFIG TESTS
# =============================================================================

class TestAuthConfig:
    """Tests for auth configuration."""

    def test_is_configured_true(self, auth_config):
        """Test is_configured returns True when properly configured."""
        assert auth_config.is_configured is True

    def test_is_configured_false_missing_url(self):
        """Test is_configured returns False when URL missing."""
        config = AuthConfig(
            supabase_url="",
            supabase_jwt_secret="secret",
        )
        assert config.is_configured is False

    def test_is_configured_false_missing_secret(self):
        """Test is_configured returns False when secret missing."""
        config = AuthConfig(
            supabase_url="https://test.supabase.co",
            supabase_jwt_secret="",
        )
        assert config.is_configured is False

    def test_supabase_project_ref(self, auth_config):
        """Test extracting project ref from URL."""
        assert auth_config.supabase_project_ref == "test"

    def test_supabase_project_ref_none(self):
        """Test project ref is None when URL not set."""
        config = AuthConfig(supabase_url="")
        assert config.supabase_project_ref is None


# =============================================================================
# INTEGRATION TESTS (require database)
# =============================================================================

@pytest.mark.asyncio
class TestAuthIntegration:
    """Integration tests for authentication (require test database)."""

    @pytest.fixture
    def db_session(self):
        """Create test database session."""
        # This would be configured in conftest.py
        from src.database.session import get_db_context
        with get_db_context() as db:
            yield db

    async def test_full_auth_flow(self, db_session, auth_config, valid_jwt_payload, create_test_token):
        """Test complete authentication flow."""
        # This test requires a real database connection
        # Skip if not available
        pytest.skip("Requires test database")

        # 1. Create a valid token
        token = create_test_token(valid_jwt_payload)

        # 2. Verify and sync user
        with patch("src.auth.jwt.get_auth_config", return_value=auth_config):
            payload = verify_supabase_token(token)

        with patch("src.auth.sync.get_auth_config", return_value=auth_config):
            user = sync_user_from_supabase(db_session, payload)

        # 3. Verify user was created
        assert user is not None
        assert user.email == valid_jwt_payload["email"]
        assert user.role == UserRole.USER

        # 4. Second sync should update, not create
        user2 = sync_user_from_supabase(db_session, payload)
        assert user2.id == user.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
