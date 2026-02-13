"""Unified cache infrastructure with multiple backend support."""

from .base import CacheProvider
from .memory import InMemoryCache
from .streamlit import StreamlitCache
from .config import (
    CACHE_TTL_QUOTE,
    CACHE_TTL_LATEST_TRADE,
    CACHE_TTL_ACCOUNT,
    CACHE_TTL_POSITIONS,
    CACHE_TTL_HISTORICAL,
    CACHE_TTL_TICKER_INFO,
    CACHE_TTL_ORDERS,
    CACHE_TTL_FILL_ACTIVITY,
)

__all__ = [
    # Base interface
    "CacheProvider",
    # Implementations
    "InMemoryCache",
    "StreamlitCache",
    # TTL constants
    "CACHE_TTL_QUOTE",
    "CACHE_TTL_LATEST_TRADE",
    "CACHE_TTL_ACCOUNT",
    "CACHE_TTL_POSITIONS",
    "CACHE_TTL_HISTORICAL",
    "CACHE_TTL_TICKER_INFO",
    "CACHE_TTL_ORDERS",
    "CACHE_TTL_FILL_ACTIVITY",
]

# Global default cache instance (in-memory for now)
# Can be replaced with StreamlitCache if deployed on Streamlit
_default_cache: CacheProvider = InMemoryCache()


def get_cache() -> CacheProvider:
    """Get the default cache provider instance."""
    return _default_cache


def set_cache(cache: CacheProvider) -> None:
    """Set a custom cache provider as default."""
    global _default_cache
    _default_cache = cache
