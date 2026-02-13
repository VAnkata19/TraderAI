"""In-memory cache implementation with TTL support and thread safety."""

import time
import threading
from typing import Any, Dict, Optional
from datetime import timedelta

from .base import CacheProvider


class InMemoryCache(CacheProvider):
    """Thread-safe in-memory cache with TTL (time-to-live) support.

    Suitable for single-process deployments or as a fallback cache.
    Automatically expires entries based on TTL.
    """

    def __init__(self):
        """Initialize empty cache with lock for thread safety."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache, checking expiry.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, otherwise None
        """
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            # Check if entry has expired
            if entry.get("expiry") and time.time() > entry["expiry"]:
                del self._cache[key]
                return None

            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """Store a value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live; if None, value persists indefinitely
        """
        with self._lock:
            expiry = None
            if ttl:
                expiry = time.time() + ttl.total_seconds()

            self._cache[key] = {"value": value, "expiry": expiry}

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Return number of currently cached items (for monitoring)."""
        with self._lock:
            return len(self._cache)
