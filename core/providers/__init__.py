"""
Unified market data provider pattern with automatic fallback chains.

This module provides a unified interface for fetching market data from multiple sources.
Providers are tried in order, with automatic fallback to the next provider on failure.
"""

from config import USE_ALPACA_DATA, USE_ALPACA_HISTORICAL

from .base import MarketDataProvider
from .alpaca_provider import AlpacaProvider
from .yfinance_provider import YFinanceProvider
from .composite_provider import CompositeProvider


def create_default_provider() -> MarketDataProvider:
    """
    Create the default provider chain based on configuration.

    Returns:
        MarketDataProvider configured according to config.py settings:
        - If Alpaca enabled: Alpaca → yfinance (with fallback)
        - Otherwise: yfinance only
    """
    providers = []

    if USE_ALPACA_DATA and USE_ALPACA_HISTORICAL:
        providers.append(AlpacaProvider())

    # Always add yfinance as fallback
    providers.append(YFinanceProvider())

    if len(providers) == 1:
        return providers[0]
    else:
        return CompositeProvider(providers)


# Global instance for convenience
_default_provider = None


def get_provider() -> MarketDataProvider:
    """
    Get or create the default market data provider.

    Returns:
        The configured MarketDataProvider instance
    """
    global _default_provider
    if _default_provider is None:
        _default_provider = create_default_provider()
    return _default_provider


__all__ = [
    "MarketDataProvider",
    "AlpacaProvider",
    "YFinanceProvider",
    "CompositeProvider",
    "create_default_provider",
    "get_provider",
]
