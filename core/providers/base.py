"""Abstract base classes for market data providers."""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class MarketDataProvider(ABC):
    """Abstract base class for market data sources."""

    @abstractmethod
    def get_historical_bars(
        self,
        ticker: str,
        period: str,
        interval: str
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data.

        Parameters:
            ticker: Stock symbol (e.g., "AAPL")
            period: Time period (e.g., "5d", "1mo", "1y")
            interval: Data interval (e.g., "1m", "5m", "1h", "1d")

        Returns:
            DataFrame with OHLCV data indexed by timestamp, or empty DataFrame on failure
        """
        pass

    @abstractmethod
    def get_ticker_info(self, ticker: str) -> Optional[dict]:
        """
        Get current ticker info (price, change, etc.).

        Parameters:
            ticker: Stock symbol (e.g., "AAPL")

        Returns:
            Dict with keys: price, prev_close, change, change_pct
            Returns None if unable to fetch
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return provider name for logging."""
        pass
