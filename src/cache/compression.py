"""
Cache Compression Utilities

Uses LZ4 for fast compression with good ratios.
Compression is applied automatically for entries larger than threshold.
"""

import json
import logging
from typing import Any, Tuple, Optional
from dataclasses import dataclass

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False

try:
    import zstandard
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False


logger = logging.getLogger(__name__)


# Compression type markers (1-byte prefix)
MARKER_UNCOMPRESSED = b'\x00'
MARKER_LZ4 = b'\x01'
MARKER_ZSTD = b'\x02'


@dataclass
class CompressionStats:
    """Track compression statistics."""
    original_size: int
    compressed_size: int
    compression_ratio: float
    algorithm: str

    @property
    def savings_percent(self) -> float:
        """Calculate space savings percentage."""
        if self.original_size == 0:
            return 0.0
        return (1 - self.compressed_size / self.original_size) * 100


class CacheCompressor:
    """
    Handles compression/decompression of cache entries.

    Uses LZ4 by default for its speed characteristics:
    - Compression: ~500 MB/s
    - Decompression: ~3000 MB/s
    - Ratio: ~2-3x for JSON data

    For large entries (>100KB), can optionally use ZSTD for better ratios.
    """

    def __init__(
        self,
        enabled: bool = True,
        threshold: int = 1024,  # 1KB minimum for compression
        use_zstd_threshold: int = 102400,  # 100KB for ZSTD
    ):
        self.enabled = enabled and LZ4_AVAILABLE
        self.threshold = threshold
        self.use_zstd_threshold = use_zstd_threshold
        self.use_zstd = ZSTD_AVAILABLE

        if enabled and not LZ4_AVAILABLE:
            logger.warning(
                "LZ4 not available. Install with: pip install lz4. "
                "Compression disabled."
            )

        # Pre-create ZSTD compressor for better performance
        if self.use_zstd:
            self._zstd_compressor = zstandard.ZstdCompressor(level=3)
            self._zstd_decompressor = zstandard.ZstdDecompressor()

    def compress(self, data: bytes) -> Tuple[bytes, Optional[CompressionStats]]:
        """
        Compress data if beneficial.

        Returns:
            Tuple of (compressed_data, stats) or (original_data, None)
        """
        if not self.enabled or len(data) < self.threshold:
            return MARKER_UNCOMPRESSED + data, None

        try:
            # Use ZSTD for large entries
            if self.use_zstd and len(data) >= self.use_zstd_threshold:
                compressed = self._zstd_compressor.compress(data)
                marker = MARKER_ZSTD
                algorithm = "zstd"
            else:
                compressed = lz4.frame.compress(data)
                marker = MARKER_LZ4
                algorithm = "lz4"

            # Only use compression if it actually saves space
            if len(compressed) < len(data):
                stats = CompressionStats(
                    original_size=len(data),
                    compressed_size=len(compressed) + 1,  # +1 for marker
                    compression_ratio=len(data) / len(compressed),
                    algorithm=algorithm,
                )
                return marker + compressed, stats

            # Compression didn't help, return uncompressed
            return MARKER_UNCOMPRESSED + data, None

        except Exception as e:
            logger.warning(f"Compression failed: {e}, storing uncompressed")
            return MARKER_UNCOMPRESSED + data, None

    def decompress(self, data: bytes) -> bytes:
        """
        Decompress data if compressed.

        Handles:
        - Uncompressed data (marker 0x00)
        - LZ4 compressed (marker 0x01)
        - ZSTD compressed (marker 0x02)
        """
        if not data:
            return data

        marker = data[0:1]
        payload = data[1:]

        try:
            if marker == MARKER_UNCOMPRESSED:
                return payload
            elif marker == MARKER_LZ4:
                if not LZ4_AVAILABLE:
                    raise RuntimeError("LZ4 not available for decompression")
                return lz4.frame.decompress(payload)
            elif marker == MARKER_ZSTD:
                if not ZSTD_AVAILABLE:
                    raise RuntimeError("ZSTD not available for decompression")
                return self._zstd_decompressor.decompress(payload)
            else:
                # Unknown marker, assume uncompressed
                logger.warning(f"Unknown compression marker: {marker}")
                return data

        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise


def serialize_value(value: Any) -> bytes:
    """
    Serialize a Python value to bytes for caching.

    Uses JSON with default handler for non-serializable types.
    """
    def default_handler(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

    json_str = json.dumps(value, default=default_handler, ensure_ascii=False)
    return json_str.encode('utf-8')


def deserialize_value(data: bytes) -> Any:
    """
    Deserialize bytes back to Python value.
    """
    if not data:
        return None
    return json.loads(data.decode('utf-8'))
