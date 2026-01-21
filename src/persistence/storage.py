"""
Storage Backends

File and S3 storage implementations for analysis data and reports.
"""

import os
import json
import gzip
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, BinaryIO
import hashlib

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def save_json(self, key: str, data: Dict) -> str:
        """Save JSON data. Returns the storage key/path."""
        pass

    @abstractmethod
    async def load_json(self, key: str) -> Optional[Dict]:
        """Load JSON data by key."""
        pass

    @abstractmethod
    async def save_binary(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Save binary data (e.g., PDFs). Returns the storage key/path."""
        pass

    @abstractmethod
    async def load_binary(self, key: str) -> Optional[bytes]:
        """Load binary data by key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete data by key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def list_keys(self, prefix: str) -> List[str]:
        """List keys with given prefix."""
        pass

    @abstractmethod
    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Get URL for accessing the stored data (if supported)."""
        pass


class FileStorage(StorageBackend):
    """
    File system storage backend.

    Stores data in local filesystem with optional compression.
    """

    def __init__(
        self,
        base_path: Optional[str] = None,
        compress: bool = True
    ):
        """
        Initialize file storage.

        Args:
            base_path: Root directory for storage.
                      Defaults to ~/.authoricy/storage/
            compress: Whether to compress JSON data
        """
        if base_path is None:
            base_path = os.getenv(
                "AUTHORICY_STORAGE_PATH",
                str(Path.home() / ".authoricy" / "storage")
            )

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.compress = compress

        logger.info(f"FileStorage initialized at {self.base_path}")

    def _get_path(self, key: str) -> Path:
        """Get full path for a key."""
        # Sanitize key and create path
        safe_key = key.replace("..", "").lstrip("/")
        return self.base_path / safe_key

    async def save_json(self, key: str, data: Dict) -> str:
        """Save JSON data with optional compression."""
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        json_str = json.dumps(data, indent=2, default=str)

        if self.compress:
            path = path.with_suffix(".json.gz")
            with gzip.open(path, "wt", encoding="utf-8") as f:
                f.write(json_str)
        else:
            path = path.with_suffix(".json")
            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)

        logger.debug(f"Saved JSON to {path}")
        return str(path.relative_to(self.base_path))

    async def load_json(self, key: str) -> Optional[Dict]:
        """Load JSON data."""
        # Try compressed first
        path = self._get_path(key)

        if path.with_suffix(".json.gz").exists():
            path = path.with_suffix(".json.gz")
            with gzip.open(path, "rt", encoding="utf-8") as f:
                return json.load(f)

        if path.with_suffix(".json").exists():
            path = path.with_suffix(".json")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        # Try exact key
        if path.exists():
            if path.suffix == ".gz":
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    return json.load(f)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)

        return None

    async def save_binary(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Save binary data."""
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            f.write(data)

        logger.debug(f"Saved binary to {path} ({len(data)} bytes)")
        return str(path.relative_to(self.base_path))

    async def load_binary(self, key: str) -> Optional[bytes]:
        """Load binary data."""
        path = self._get_path(key)

        if not path.exists():
            return None

        with open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        """Delete data by key."""
        path = self._get_path(key)

        # Try various extensions
        for suffix in ["", ".json", ".json.gz", ".pdf"]:
            p = path.with_suffix(suffix) if suffix else path
            if p.exists():
                p.unlink()
                logger.debug(f"Deleted {p}")
                return True

        return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        path = self._get_path(key)

        for suffix in ["", ".json", ".json.gz", ".pdf"]:
            p = path.with_suffix(suffix) if suffix else path
            if p.exists():
                return True

        return False

    async def list_keys(self, prefix: str = "") -> List[str]:
        """List keys with given prefix."""
        search_path = self._get_path(prefix) if prefix else self.base_path

        if not search_path.exists():
            return []

        keys = []
        if search_path.is_dir():
            for path in search_path.rglob("*"):
                if path.is_file():
                    rel_path = str(path.relative_to(self.base_path))
                    keys.append(rel_path)
        else:
            keys.append(str(search_path.relative_to(self.base_path)))

        return sorted(keys)

    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """File storage doesn't support URLs directly."""
        path = self._get_path(key)
        if path.exists():
            return f"file://{path.absolute()}"
        return None


class S3Storage(StorageBackend):
    """
    AWS S3 storage backend.

    Requires boto3 and AWS credentials.
    """

    def __init__(
        self,
        bucket: Optional[str] = None,
        prefix: str = "authoricy/",
        region: Optional[str] = None
    ):
        """
        Initialize S3 storage.

        Args:
            bucket: S3 bucket name. Defaults to AUTHORICY_S3_BUCKET env var.
            prefix: Key prefix within bucket.
            region: AWS region. Defaults to AUTHORICY_S3_REGION or us-east-1.
        """
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError("boto3 required for S3 storage: pip install boto3")

        self.bucket = bucket or os.getenv("AUTHORICY_S3_BUCKET")
        if not self.bucket:
            raise ValueError("S3 bucket not specified")

        self.prefix = prefix
        self.region = region or os.getenv("AUTHORICY_S3_REGION", "us-east-1")

        config = Config(
            region_name=self.region,
            retries={"max_attempts": 3}
        )

        self.s3 = boto3.client("s3", config=config)
        logger.info(f"S3Storage initialized for bucket {self.bucket}")

    def _get_key(self, key: str) -> str:
        """Get full S3 key with prefix."""
        return f"{self.prefix}{key}"

    async def save_json(self, key: str, data: Dict) -> str:
        """Save JSON data to S3."""
        s3_key = self._get_key(key)
        if not s3_key.endswith(".json"):
            s3_key += ".json"

        json_bytes = json.dumps(data, indent=2, default=str).encode("utf-8")

        self.s3.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=json_bytes,
            ContentType="application/json"
        )

        logger.debug(f"Saved JSON to s3://{self.bucket}/{s3_key}")
        return s3_key

    async def load_json(self, key: str) -> Optional[Dict]:
        """Load JSON data from S3."""
        s3_key = self._get_key(key)
        if not s3_key.endswith(".json"):
            s3_key += ".json"

        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
            return json.loads(response["Body"].read().decode("utf-8"))
        except self.s3.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.error(f"Failed to load from S3: {e}")
            return None

    async def save_binary(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Save binary data to S3."""
        s3_key = self._get_key(key)

        self.s3.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=data,
            ContentType=content_type
        )

        logger.debug(f"Saved binary to s3://{self.bucket}/{s3_key}")
        return s3_key

    async def load_binary(self, key: str) -> Optional[bytes]:
        """Load binary data from S3."""
        s3_key = self._get_key(key)

        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"Failed to load binary from S3: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete data from S3."""
        s3_key = self._get_key(key)

        try:
            self.s3.delete_object(Bucket=self.bucket, Key=s3_key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete from S3: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in S3."""
        s3_key = self._get_key(key)

        try:
            self.s3.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except:
            return False

    async def list_keys(self, prefix: str = "") -> List[str]:
        """List keys with given prefix."""
        s3_prefix = self._get_key(prefix)

        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            keys = []

            for page in paginator.paginate(Bucket=self.bucket, Prefix=s3_prefix):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])

            return keys
        except Exception as e:
            logger.error(f"Failed to list S3 keys: {e}")
            return []

    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate presigned URL for S3 object."""
        s3_key = self._get_key(key)

        try:
            url = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None


def get_storage_backend() -> StorageBackend:
    """
    Get the configured storage backend.

    Returns FileStorage by default, S3Storage if AUTHORICY_S3_BUCKET is set.
    """
    if os.getenv("AUTHORICY_S3_BUCKET"):
        return S3Storage()
    return FileStorage()
