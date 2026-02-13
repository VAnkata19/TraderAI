"""yfinance implementation of MarketDataProvider."""

from typing import Optional

import pandas as pd
import yfinance as yf

from .base import MarketDataProvider


class YFinanceProvider(MarketDataProvider):
    """yfinance market data provider with robust fallback behavior."""

    def get_historical_bars(
        self,
        ticker: str,
        period: str,
        interval: str
    ) -> pd.DataFrame:
        """Get historical bars from yfinance."""
        try:
            stock = yf.Ticker(ticker)
            # Include pre-market and after-hours data for most current information
            df = stock.history(period=period, interval=interval, prepost=True)
            return df
        except Exception:
            return pd.DataFrame()

    def get_ticker_info(self, ticker: str) -> Optional[dict]:
        """
        Get ticker info from yfinance with 3-level fallback:
        1. stock.info (most accurate)
        2. stock.fast_info (faster but less reliable)
        3. Historical data (most reliable if others fail)
        """
        stock = yf.Ticker(ticker)

        # Level 1: Try stock.info
        try:
            info = stock.info
            prev = info.get("previousClose")
            last = info.get("currentPrice") or info.get("regularMarketPrice")

            if last is not None and prev is not None and prev > 0:
                return {
                    "price": float(last),
                    "prev_close": float(prev),
                    "change": float(last - prev),
                    "change_pct": ((last - prev) / prev) * 100,
                }
        except Exception:
            pass

        # Level 2: Try fast_info
        try:
            fast_info = stock.fast_info
            prev = fast_info.get("previousClose")
            last = fast_info.get("lastPrice")

            if last is not None and prev is not None and prev > 0:
                return {
                    "price": float(last),
                    "prev_close": float(prev),
                    "change": float(last - prev),
                    "change_pct": ((last - prev) / prev) * 100,
                }
        except Exception:
            pass

        # Level 3: Try historical data
        try:
            hist = stock.history(period="5d", interval="1d")
            if len(hist) >= 2:
                last = hist.iloc[-1]["Close"]
                prev = hist.iloc[-2]["Close"]
            elif len(hist) >= 1:
                last = hist.iloc[-1]["Close"]
                prev = hist.iloc[-1]["Open"]
            else:
                return None

            if prev and prev > 0:
                return {
                    "price": float(last),
                    "prev_close": float(prev),
                    "change": float(last - prev),
                    "change_pct": ((last - prev) / prev) * 100,
                }
        except Exception:
            pass

        return None

    def get_name(self) -> str:
        """Return provider name."""
        return "yfinance"
