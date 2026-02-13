"""Composite provider implementing fallback chain pattern."""

from typing import List, Optional

import pandas as pd

from .base import MarketDataProvider


class CompositeProvider(MarketDataProvider):
    """Chain of responsibility pattern for data providers with automatic fallback."""

    def __init__(self, providers: List[MarketDataProvider]):
        """
        Initialize with a list of providers to try in order.

        Parameters:
            providers: List of MarketDataProvider instances, ordered by preference
        """
        self.providers = providers

    def get_historical_bars(
        self,
        ticker: str,
        period: str,
        interval: str
    ) -> pd.DataFrame:
        """Try each provider in order until one succeeds."""
        errors = []

        for provider in self.providers:
            try:
                result = provider.get_historical_bars(ticker, period, interval)
                if result is not None and not result.empty:
                    print(f"[PROVIDER] Historical bars success: {provider.get_name()}")
                    return result
            except Exception as e:
                error_msg = f"{provider.get_name()} failed: {e}"
                errors.append(error_msg)
                print(f"[PROVIDER] {error_msg}")

        # All providers failed
        print(f"[PROVIDER] All providers failed for historical bars: {'; '.join(errors)}")
        return pd.DataFrame()

    def get_ticker_info(self, ticker: str) -> Optional[dict]:
        """Try each provider in order until one succeeds."""
        errors = []

        for provider in self.providers:
            try:
                result = provider.get_ticker_info(ticker)
                if result is not None:
                    print(f"[PROVIDER] Ticker info success: {provider.get_name()}")
                    return result
            except Exception as e:
                error_msg = f"{provider.get_name()} failed: {e}"
                errors.append(error_msg)
                print(f"[PROVIDER] {error_msg}")

        # All providers failed
        print(f"[PROVIDER] All providers failed for ticker info: {'; '.join(errors)}")
        return None

    def get_name(self) -> str:
        """Return composite provider name with list of sub-providers."""
        provider_names = ", ".join(p.get_name() for p in self.providers)
        return f"Composite[{provider_names}]"
