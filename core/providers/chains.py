"""Pre-configured provider chains for different use cases."""

from config import USE_ALPACA_DATA, USE_ALPACA_HISTORICAL
from .alpaca_provider import AlpacaProvider
from .yfinance_provider import YFinanceProvider
from .composite_provider import CompositeProvider
from .base import MarketDataProvider


def create_historical_bars_chain() -> MarketDataProvider:
    """Create provider chain for historical OHLCV data.

    Uses Alpaca first (if enabled and configured), falls back to yfinance.

    Returns:
        MarketDataProvider configured for historical bars fetching
    """
    providers = []

    if USE_ALPACA_DATA and USE_ALPACA_HISTORICAL:
        providers.append(AlpacaProvider())

    # Always add yfinance as fallback
    providers.append(YFinanceProvider())

    if len(providers) == 1:
        return providers[0]
    return CompositeProvider(providers)


def create_ticker_info_chain() -> MarketDataProvider:
    """Create provider chain for ticker info (price, change, etc.).

    Uses Alpaca first (if enabled), falls back to yfinance.

    Returns:
        MarketDataProvider configured for ticker info fetching
    """
    providers = []

    if USE_ALPACA_DATA:
        providers.append(AlpacaProvider())

    # Always add yfinance as fallback
    providers.append(YFinanceProvider())

    if len(providers) == 1:
        return providers[0]
    return CompositeProvider(providers)


# Global instances for convenience
_historical_bars_chain = None
_ticker_info_chain = None


def get_historical_bars_chain() -> MarketDataProvider:
    """Get or create the historical bars provider chain.

    Returns:
        Cached MarketDataProvider instance for bars
    """
    global _historical_bars_chain
    if _historical_bars_chain is None:
        _historical_bars_chain = create_historical_bars_chain()
    return _historical_bars_chain


def get_ticker_info_chain() -> MarketDataProvider:
    """Get or create the ticker info provider chain.

    Returns:
        Cached MarketDataProvider instance for ticker info
    """
    global _ticker_info_chain
    if _ticker_info_chain is None:
        _ticker_info_chain = create_ticker_info_chain()
    return _ticker_info_chain
