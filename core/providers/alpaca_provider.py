"""Alpaca implementation of MarketDataProvider."""

from typing import Optional

import pandas as pd

from .base import MarketDataProvider
from core.alpaca import (
    get_historical_bars_alpaca,
    get_ticker_info_alpaca,
)


class AlpacaProvider(MarketDataProvider):
    """Alpaca market data provider."""

    def get_historical_bars(
        self,
        ticker: str,
        period: str,
        interval: str
    ) -> pd.DataFrame:
        """Get historical bars from Alpaca."""
        try:
            return get_historical_bars_alpaca(ticker, period, interval)
        except Exception:
            return pd.DataFrame()

    def get_ticker_info(self, ticker: str) -> Optional[dict]:
        """Get ticker info from Alpaca."""
        return get_ticker_info_alpaca(ticker)

    def get_name(self) -> str:
        """Return provider name."""
        return "Alpaca"
