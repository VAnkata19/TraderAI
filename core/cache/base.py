"""Abstract base class for cache providers with unified interface."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, TypeVar
from datetime import timedelta

T = TypeVar("T")


class CacheProvider(ABC):
    """Abstract base class for cache implementations.

    Provides a unified interface for different caching backends (memory, Streamlit, Redis, etc.)
    with support for TTL (time-to-live) and automatic fetch-if-missing semantics.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache by key.

        Args:
            key: Cache key

        Returns:
            Cached value, or None if not found or expired
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """Store a value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live; if None, value persists for cache lifetime
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass

    def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], T],
        ttl: Optional[timedelta] = None,
    ) -> T:
        """Get from cache or fetch and cache if missing.

        This is the primary convenience method for typical cache usage:
        - Returns cached value if available
        - Otherwise calls fetch_fn(), caches result, and returns it

        Args:
            key: Cache key
            fetch_fn: Function to call if cache miss (should return T)
            ttl: Time-to-live for cached result

        Returns:
            Cached or freshly fetched value
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        value = fetch_fn()
        self.set(key, value, ttl)
        return value
