"""
API Key Management

Generate, validate, and manage API keys.
"""

import os
import secrets
import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    """API Key data model."""
    key_id: str
    name: str
    key_hash: str  # SHA-256 hash of the actual key
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    rate_limit_multiplier: float = 1.0
    metadata: Dict = field(default_factory=dict)
    is_active: bool = True

    def is_expired(self) -> bool:
        """Check if key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)."""
        return self.is_active and not self.is_expired()

    def has_permission(self, permission: str) -> bool:
        """Check if key has a specific permission."""
        return "*" in self.permissions or permission in self.permissions

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        if self.last_used_at:
            data["last_used_at"] = self.last_used_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "APIKey":
        """Create from dictionary."""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("expires_at"):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        if data.get("last_used_at"):
            data["last_used_at"] = datetime.fromisoformat(data["last_used_at"])
        return cls(**data)


class APIKeyManager:
    """
    Manages API keys with persistent storage.

    Supports file-based or database storage.
    """

    # Permission constants
    PERM_ANALYZE = "analyze"
    PERM_REPORTS = "reports"
    PERM_ADMIN = "admin"
    PERM_ALL = "*"

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize key manager.

        Args:
            storage_path: Path to JSON file for key storage.
                         Defaults to ~/.authoricy/api_keys.json
        """
        if storage_path is None:
            storage_path = os.getenv(
                "AUTHORICY_KEYS_PATH",
                str(Path.home() / ".authoricy" / "api_keys.json")
            )

        self.storage_path = Path(storage_path)
        self._keys: Dict[str, APIKey] = {}
        self._load_keys()

    def _load_keys(self):
        """Load keys from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for key_id, key_data in data.items():
                        self._keys[key_id] = APIKey.from_dict(key_data)
                logger.info(f"Loaded {len(self._keys)} API keys from storage")
            except Exception as e:
                logger.error(f"Failed to load API keys: {e}")

        # Load master key from environment if not in storage
        master_key = os.getenv("AUTHORICY_MASTER_API_KEY")
        if master_key:
            key_hash = self._hash_key(master_key)
            if not any(k.key_hash == key_hash for k in self._keys.values()):
                self._add_key_internal(
                    name="Master Key (env)",
                    key_hash=key_hash,
                    permissions=[self.PERM_ALL],
                    rate_limit_multiplier=10.0
                )

    def _save_keys(self):
        """Persist keys to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {k: v.to_dict() for k, v in self._keys.items()}
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self._keys)} API keys to storage")
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")

    def _hash_key(self, key: str) -> str:
        """Create hash of API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def _generate_key_id(self) -> str:
        """Generate unique key ID."""
        return f"ak_{secrets.token_hex(8)}"

    def _add_key_internal(
        self,
        name: str,
        key_hash: str,
        permissions: List[str],
        rate_limit_multiplier: float = 1.0,
        expires_days: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> APIKey:
        """Internal method to add a key with known hash."""
        key_id = self._generate_key_id()

        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)

        api_key = APIKey(
            key_id=key_id,
            name=name,
            key_hash=key_hash,
            permissions=permissions,
            created_at=datetime.now(),
            expires_at=expires_at,
            rate_limit_multiplier=rate_limit_multiplier,
            metadata=metadata or {}
        )

        self._keys[key_id] = api_key
        self._save_keys()

        return api_key

    def create_key(
        self,
        name: str,
        permissions: Optional[List[str]] = None,
        expires_days: Optional[int] = None,
        rate_limit_multiplier: float = 1.0,
        metadata: Optional[Dict] = None
    ) -> tuple[str, APIKey]:
        """
        Create a new API key.

        Returns:
            Tuple of (raw_key, APIKey object)
            IMPORTANT: raw_key is only returned once and cannot be recovered!
        """
        if permissions is None:
            permissions = [self.PERM_ANALYZE, self.PERM_REPORTS]

        # Generate secure random key
        raw_key = f"auth_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)

        api_key = self._add_key_internal(
            name=name,
            key_hash=key_hash,
            permissions=permissions,
            rate_limit_multiplier=rate_limit_multiplier,
            expires_days=expires_days,
            metadata=metadata
        )

        logger.info(f"Created API key: {api_key.key_id} ({name})")
        return raw_key, api_key

    def validate_key(self, raw_key: str) -> tuple[bool, Optional[APIKey]]:
        """
        Validate an API key.

        Returns:
            Tuple of (is_valid, APIKey or None)
        """
        if not raw_key:
            return False, None

        key_hash = self._hash_key(raw_key)

        for api_key in self._keys.values():
            if api_key.key_hash == key_hash:
                if api_key.is_valid():
                    # Update last used
                    api_key.last_used_at = datetime.now()
                    api_key.usage_count += 1
                    self._save_keys()
                    return True, api_key
                else:
                    return False, api_key

        return False, None

    def get_key(self, key_id: str) -> Optional[APIKey]:
        """Get key by ID."""
        return self._keys.get(key_id)

    def list_keys(self, include_inactive: bool = False) -> List[APIKey]:
        """List all API keys."""
        keys = list(self._keys.values())
        if not include_inactive:
            keys = [k for k in keys if k.is_active]
        return sorted(keys, key=lambda k: k.created_at, reverse=True)

    def revoke_key(self, key_id: str) -> bool:
        """Revoke (deactivate) an API key."""
        if key_id in self._keys:
            self._keys[key_id].is_active = False
            self._save_keys()
            logger.info(f"Revoked API key: {key_id}")
            return True
        return False

    def delete_key(self, key_id: str) -> bool:
        """Permanently delete an API key."""
        if key_id in self._keys:
            del self._keys[key_id]
            self._save_keys()
            logger.info(f"Deleted API key: {key_id}")
            return True
        return False

    def update_permissions(self, key_id: str, permissions: List[str]) -> bool:
        """Update permissions for a key."""
        if key_id in self._keys:
            self._keys[key_id].permissions = permissions
            self._save_keys()
            return True
        return False

    def rotate_key(self, key_id: str) -> Optional[tuple[str, APIKey]]:
        """
        Rotate an API key (create new, revoke old).

        Returns:
            Tuple of (new_raw_key, new_APIKey) or None if key not found
        """
        old_key = self._keys.get(key_id)
        if not old_key:
            return None

        # Create new key with same settings
        new_raw_key, new_api_key = self.create_key(
            name=f"{old_key.name} (rotated)",
            permissions=old_key.permissions.copy(),
            rate_limit_multiplier=old_key.rate_limit_multiplier,
            metadata={
                **old_key.metadata,
                "rotated_from": key_id,
                "rotated_at": datetime.now().isoformat()
            }
        )

        # Revoke old key
        self.revoke_key(key_id)

        logger.info(f"Rotated API key: {key_id} -> {new_api_key.key_id}")
        return new_raw_key, new_api_key
