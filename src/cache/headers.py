"""
HTTP Cache Headers

Manages Cache-Control, ETag, and related headers for CDN and browser caching.
Implements stale-while-revalidate pattern for optimal UX.

HTTP caching layers:
1. Browser: Uses Cache-Control and stale-while-revalidate
2. CDN: Uses Surrogate-Key for selective purging
3. Conditional requests: Uses ETag for 304 Not Modified
"""

import hashlib
import logging
from datetime import datetime
from functools import wraps
from typing import Optional, List, Callable, Any

from fastapi import Response, Request


logger = logging.getLogger(__name__)


def generate_etag(
    *components: Any,
    weak: bool = False,
) -> str:
    """
    Generate ETag from components.

    Args:
        components: Values to hash for ETag
        weak: If True, generates a weak ETag (W/"...")

    Returns:
        ETag string with quotes
    """
    hash_input = ":".join(str(c) for c in components)
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:16]

    if weak:
        return f'W/"{hash_value}"'
    return f'"{hash_value}"'


def parse_etag(etag: str) -> str:
    """Parse ETag value, removing quotes and weak prefix."""
    if not etag:
        return ""

    # Remove weak prefix
    if etag.startswith("W/"):
        etag = etag[2:]

    # Remove quotes
    return etag.strip('"')


def etags_match(
    request_etag: Optional[str],
    current_etag: str,
) -> bool:
    """
    Check if request ETag matches current ETag.

    Handles:
    - Strong comparison (exact match)
    - Weak comparison (ignores W/ prefix)
    - Multiple ETags in If-None-Match
    """
    if not request_etag:
        return False

    current = parse_etag(current_etag)

    # Handle multiple ETags (comma-separated)
    for etag in request_etag.split(","):
        etag = etag.strip()

        # Handle wildcard
        if etag == "*":
            return True

        if parse_etag(etag) == current:
            return True

    return False


class CacheHeadersBuilder:
    """
    Fluent builder for HTTP cache headers.

    Usage:
        headers = (CacheHeadersBuilder()
            .max_age(300)
            .stale_while_revalidate(600)
            .public()
            .etag(analysis_id, updated_at)
            .surrogate_keys(["domain:123", "dashboard"])
            .build())
    """

    def __init__(self):
        self._max_age: int = 0
        self._swr: int = 0
        self._stale_if_error: int = 0
        self._public: bool = True
        self._no_cache: bool = False
        self._no_store: bool = False
        self._must_revalidate: bool = False
        self._etag: Optional[str] = None
        self._last_modified: Optional[datetime] = None
        self._surrogate_keys: List[str] = []
        self._vary: List[str] = []

    def max_age(self, seconds: int) -> "CacheHeadersBuilder":
        """Set max-age directive."""
        self._max_age = seconds
        return self

    def stale_while_revalidate(self, seconds: int) -> "CacheHeadersBuilder":
        """Set stale-while-revalidate directive."""
        self._swr = seconds
        return self

    def stale_if_error(self, seconds: int) -> "CacheHeadersBuilder":
        """Set stale-if-error directive."""
        self._stale_if_error = seconds
        return self

    def public(self) -> "CacheHeadersBuilder":
        """Mark response as cacheable by CDN."""
        self._public = True
        return self

    def private(self) -> "CacheHeadersBuilder":
        """Mark response as not cacheable by CDN."""
        self._public = False
        return self

    def no_cache(self) -> "CacheHeadersBuilder":
        """Require revalidation before serving."""
        self._no_cache = True
        return self

    def no_store(self) -> "CacheHeadersBuilder":
        """Disable all caching."""
        self._no_store = True
        return self

    def must_revalidate(self) -> "CacheHeadersBuilder":
        """Require revalidation after max-age."""
        self._must_revalidate = True
        return self

    def etag(self, *components: Any, weak: bool = False) -> "CacheHeadersBuilder":
        """Generate and set ETag from components."""
        self._etag = generate_etag(*components, weak=weak)
        return self

    def etag_value(self, value: str) -> "CacheHeadersBuilder":
        """Set pre-computed ETag value."""
        self._etag = value
        return self

    def last_modified(self, dt: datetime) -> "CacheHeadersBuilder":
        """Set Last-Modified header."""
        self._last_modified = dt
        return self

    def surrogate_keys(self, keys: List[str]) -> "CacheHeadersBuilder":
        """Set surrogate keys for CDN purging."""
        self._surrogate_keys.extend(keys)
        return self

    def vary(self, headers: List[str]) -> "CacheHeadersBuilder":
        """Set Vary header for cache key variation."""
        self._vary.extend(headers)
        return self

    def build(self) -> dict:
        """Build headers dictionary."""
        headers = {}

        # Build Cache-Control
        directives = []

        if self._no_store:
            directives.append("no-store")
        else:
            directives.append("public" if self._public else "private")

            if self._no_cache:
                directives.append("no-cache")

            if self._max_age > 0:
                directives.append(f"max-age={self._max_age}")

            if self._swr > 0:
                directives.append(f"stale-while-revalidate={self._swr}")

            if self._stale_if_error > 0:
                directives.append(f"stale-if-error={self._stale_if_error}")

            if self._must_revalidate:
                directives.append("must-revalidate")

        if directives:
            headers["Cache-Control"] = ", ".join(directives)

        # ETag
        if self._etag:
            headers["ETag"] = self._etag

        # Last-Modified
        if self._last_modified:
            headers["Last-Modified"] = self._last_modified.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )

        # Surrogate keys for CDN
        if self._surrogate_keys:
            # Cloudflare Cache-Tag format
            headers["Cache-Tag"] = ",".join(self._surrogate_keys)
            # Fastly/Varnish Surrogate-Key format
            headers["Surrogate-Key"] = " ".join(self._surrogate_keys)

        # Vary
        if self._vary:
            headers["Vary"] = ", ".join(self._vary)

        return headers

    def apply(self, response: Response) -> Response:
        """Apply headers to FastAPI Response."""
        for key, value in self.build().items():
            response.headers[key] = value
        return response


def cache_headers(
    max_age: int = 300,
    stale_while_revalidate: Optional[int] = None,
    public: bool = True,
    surrogate_keys: Optional[List[str]] = None,
    vary: Optional[List[str]] = None,
):
    """
    Decorator to add cache headers to FastAPI endpoint.

    Usage:
        @router.get("/{domain_id}/overview")
        @cache_headers(max_age=300, surrogate_keys=["dashboard"])
        async def get_overview(domain_id: str):
            ...

    Args:
        max_age: Cache duration in seconds
        stale_while_revalidate: SWR duration (defaults to max_age * 2)
        public: Whether response can be cached by CDN
        surrogate_keys: Keys for selective CDN purging
        vary: Headers to vary cache key on
    """
    if stale_while_revalidate is None:
        stale_while_revalidate = max_age * 2

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Find Response in kwargs or args
            response = kwargs.get("response")
            if response is None:
                for arg in args:
                    if isinstance(arg, Response):
                        response = arg
                        break

            if response is not None:
                builder = (
                    CacheHeadersBuilder()
                    .max_age(max_age)
                    .stale_while_revalidate(stale_while_revalidate)
                )

                if public:
                    builder.public()
                else:
                    builder.private()

                if surrogate_keys:
                    builder.surrogate_keys(surrogate_keys)

                if vary:
                    builder.vary(vary)

                builder.apply(response)

            return result

        return wrapper

    return decorator


def add_cache_headers(
    response: Response,
    max_age: int,
    etag: Optional[str] = None,
    last_modified: Optional[datetime] = None,
    public: bool = True,
    surrogate_keys: Optional[List[str]] = None,
) -> Response:
    """
    Add cache headers to a response.

    Convenience function for cases where decorator doesn't fit.

    Args:
        response: FastAPI Response object
        max_age: Cache duration in seconds
        etag: ETag value for conditional requests
        last_modified: When data was last changed
        public: Whether cacheable by CDN
        surrogate_keys: Keys for CDN purging

    Returns:
        Response with headers applied
    """
    builder = (
        CacheHeadersBuilder()
        .max_age(max_age)
        .stale_while_revalidate(max_age * 2)
        .stale_if_error(max_age * 4)
    )

    if public:
        builder.public()
    else:
        builder.private()

    if etag:
        builder.etag_value(etag)

    if last_modified:
        builder.last_modified(last_modified)

    if surrogate_keys:
        builder.surrogate_keys(surrogate_keys)

    return builder.apply(response)


def check_not_modified(
    request: Request,
    etag: str,
    last_modified: Optional[datetime] = None,
) -> Optional[Response]:
    """
    Check if client has current version (304 Not Modified).

    Returns a 304 Response if client cache is valid, None otherwise.

    Usage:
        not_modified = check_not_modified(request, etag, updated_at)
        if not_modified:
            return not_modified
        # Continue with normal response...
    """
    # Check If-None-Match (ETag)
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and etags_match(if_none_match, etag):
        response = Response(status_code=304)
        response.headers["ETag"] = etag
        return response

    # Check If-Modified-Since
    if last_modified:
        if_modified_since = request.headers.get("If-Modified-Since")
        if if_modified_since:
            try:
                # Parse HTTP date
                from email.utils import parsedate_to_datetime
                ims = parsedate_to_datetime(if_modified_since)
                if last_modified <= ims:
                    response = Response(status_code=304)
                    response.headers["Last-Modified"] = last_modified.strftime(
                        "%a, %d %b %Y %H:%M:%S GMT"
                    )
                    return response
            except Exception:
                pass

    return None


# Preset configurations for common use cases
CACHE_PRESET_DASHBOARD = {
    "max_age": 300,  # 5 minutes
    "stale_while_revalidate": 600,
    "public": True,
}

CACHE_PRESET_KEYWORDS = {
    "max_age": 600,  # 10 minutes
    "stale_while_revalidate": 1200,
    "public": True,
}

CACHE_PRESET_STRATEGY = {
    "max_age": 60,  # 1 minute
    "stale_while_revalidate": 120,
    "public": False,  # User-specific
}

CACHE_PRESET_REALTIME = {
    "max_age": 0,
    "no_store": True,
}
