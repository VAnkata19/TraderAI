"""Caching and rate limiting for Alpaca API calls using unified cache infrastructure."""

import time
from typing import Any, Callable, List

from config import ALPACA_RATE_LIMIT_PER_MINUTE
from core.cache import InMemoryCache


class AlpacaRateLimiter:
    """Rate limiter for Alpaca API to manage free plan limits.

    Tracks request timestamps and enforces the configured rate limit.
    Works alongside the unified cache system.
    """

    def __init__(self, limit_per_minute: int):
        """Initialize rate limiter.

        Args:
            limit_per_minute: Maximum allowed requests per minute
        """
        self._limit = limit_per_minute
        self._request_times: List[float] = []

    def is_rate_limited(self) -> bool:
        """Check if we're at or approaching the rate limit."""
        now = time.time()
        # Remove requests older than 1 minute
        self._request_times = [t for t in self._request_times if now - t < 60]
        return len(self._request_times) >= self._limit

    def record_request(self):
        """Record a new API request timestamp."""
        self._request_times.append(time.time())

    def request_count(self) -> int:
        """Get current request count in the last minute."""
        now = time.time()
        return len([t for t in self._request_times if now - t < 60])


# Global instances: unified cache + rate limiter
_cache = InMemoryCache()
_rate_limiter = AlpacaRateLimiter(ALPACA_RATE_LIMIT_PER_MINUTE)


def get_cached_or_fetch(key: str, fetch_fn: Callable, ttl: Any) -> Any:
    """Get from cache or fetch new data with rate limit protection.

    Args:
        key: Cache key
        fetch_fn: Function to call to fetch data
        ttl: Timedelta for cache TTL

    Returns:
        Cached or freshly fetched data

    Raises:
        Exception: If rate limited and no cached data available
    """
    # Try to get from cache first
    cached = _cache.get(key)
    if cached is not None:
        return cached

    # Check rate limiting before making request
    if _rate_limiter.is_rate_limited():
        print(
            f"[ALPACA] Rate limit approached "
            f"({_rate_limiter.request_count()} requests in last minute)"
        )
        # If we have stale cache, return it
        if cached is not None:
            print(f"[ALPACA] Returning stale cache for {key}")
            return cached
        raise Exception("Rate limited and no cached data available")

    # Fetch new data
    _rate_limiter.record_request()
    data = fetch_fn()
    _cache.set(key, data, ttl)
    return data


def clear_alpaca_cache():
    """Clear all cached Alpaca data to force fresh requests."""
    _cache.clear()
    print("[ALPACA] Cache cleared")
