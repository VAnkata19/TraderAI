"""Streamlit cache wrapper implementing unified CacheProvider interface."""

from typing import Any, Callable, Optional
from datetime import timedelta

from .base import CacheProvider


class StreamlitCache(CacheProvider):
    """Wrapper around Streamlit's @st.cache_data for unified cache interface.

    Delegates to Streamlit's built-in caching when available.
    Falls back to no-op cache in non-Streamlit contexts.
    """

    def __init__(self):
        """Initialize Streamlit cache wrapper."""
        self._streamlit_available = False
        self._fallback_cache = {}

        # Try to import Streamlit
        try:
            import streamlit as st
            self._st = st
            self._streamlit_available = True
        except ImportError:
            self._st = None

    def get(self, key: str) -> Optional[Any]:
        """Retrieve from Streamlit session state or fallback cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if self._streamlit_available and self._st:
            try:
                if key in self._st.session_state:
                    return self._st.session_state[key]
            except Exception:
                # If session_state access fails, fall through to fallback
                pass

        return self._fallback_cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """Store in Streamlit session state or fallback cache.

        Note: TTL is not supported by Streamlit session state (persists for session lifetime).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Ignored in Streamlit context
        """
        if self._streamlit_available and self._st:
            try:
                self._st.session_state[key] = value
                return
            except Exception:
                # If session_state write fails, fall through to fallback
                pass

        self._fallback_cache[key] = value

    def clear(self) -> None:
        """Clear both Streamlit session state and fallback cache."""
        if self._streamlit_available and self._st:
            try:
                for key in list(self._st.session_state.keys()):
                    del self._st.session_state[key]
            except Exception:
                pass

        self._fallback_cache.clear()
