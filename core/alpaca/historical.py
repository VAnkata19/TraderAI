"""Historical market data fetching for Alpaca."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import requests

from core.cache.config import CACHE_TTL_HISTORICAL, CACHE_TTL_QUOTE

from .client import get_headers, data_url
from .market_data import get_latest_trade
from .cache import get_cached_or_fetch


def _convert_period_to_dates(period: str, interval: str) -> Tuple[str, str]:
    """Convert yfinance-style period/interval to Alpaca start/end dates."""
    now = datetime.now(timezone.utc)

    # Parse period
    if period.endswith("d"):
        days = int(period[:-1])
        start = now - timedelta(days=days)
    elif period.endswith("mo"):
        months = int(period[:-2])
        start = now - timedelta(days=months * 30)
    elif period.endswith("y"):
        years = int(period[:-1])
        start = now - timedelta(days=years * 365)
    else:
        # Default to 5 days
        start = now - timedelta(days=5)

    return start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")


def _convert_interval_to_timeframe(interval: str) -> str:
    """Convert yfinance interval to Alpaca timeframe."""
    interval_map = {
        "1m": "1Min",
        "2m": "2Min",
        "5m": "5Min",
        "15m": "15Min",
        "30m": "30Min",
        "60m": "1Hour",
        "1h": "1Hour",
        "1d": "1Day",
        "5d": "1Day",
        "1wk": "1Week",
        "1mo": "1Month"
    }
    return interval_map.get(interval, "5Min")


def get_historical_bars_alpaca(
    ticker: str,
    period: str = "5d",
    interval: str = "5m"
) -> pd.DataFrame:
    """
    Get historical OHLCV data from Alpaca, returns DataFrame compatible with yfinance format.

    Parameters:
        ticker: Stock symbol (e.g., "AAPL")
        period: Time period (e.g., "5d", "1mo", "1y")
        interval: Data interval (e.g., "1m", "5m", "1h", "1d")

    Returns:
        pandas.DataFrame with OHLCV data, indexed by timestamp
    """

    def _fetch_bars():
        start_date, end_date = _convert_period_to_dates(period, interval)
        timeframe = _convert_interval_to_timeframe(interval)

        # Configuration for free plan compatibility
        params = {
            "symbols": ticker,
            "timeframe": timeframe,
            "start": start_date,
            "end": end_date,
            "limit": 1000,  # Reduced limit for free plan
            "adjustment": "raw",
        }
        # Note: Removed 'feed=sip' as it requires paid subscription

        resp = requests.get(
            data_url("/v2/stocks/bars"),
            headers=get_headers(),
            params=params,
            timeout=10,
        )

        if resp.status_code == 403:
            raise Exception(
                f"Alpaca API access denied (403). Free plan may have limited access to historical data. "
                f"Status: {resp.status_code}"
            )

        resp.raise_for_status()
        data = resp.json()

        if "bars" not in data or ticker not in data["bars"]:
            return pd.DataFrame()

        bars = data["bars"][ticker]
        if not bars:
            return pd.DataFrame()

        # Convert to DataFrame with yfinance-compatible format
        df_data = []
        for bar in bars:
            df_data.append({
                "Open": bar["o"],
                "High": bar["h"],
                "Low": bar["l"],
                "Close": bar["c"],
                "Volume": bar["v"],
                "Timestamp": pd.to_datetime(bar["t"])
            })

        df = pd.DataFrame(df_data)
        df.set_index("Timestamp", inplace=True)

        # Ensure index is DatetimeIndex and remove timezone for yfinance compatibility
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        return df

    # Use caching to avoid hitting rate limits
    cache_key = f"bars_{ticker}_{period}_{interval}"
    return get_cached_or_fetch(
        cache_key,
        _fetch_bars,
        CACHE_TTL_HISTORICAL
    )


def get_current_price_cached(ticker: str) -> float:
    """Get current price with caching to reduce API calls."""

    def _fetch_price():
        trade = get_latest_trade(ticker)
        return float(trade["p"])

    cache_key = f"price_{ticker}"
    return get_cached_or_fetch(
        cache_key,
        _fetch_price,
        CACHE_TTL_QUOTE
    )


def get_ticker_info_alpaca(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get ticker info (current price, change, etc.) from Alpaca,
    formatted similarly to yfinance fast_info.
    """

    def _fetch_info():
        try:
            # Get current trade for latest price
            trade = get_latest_trade(ticker)
            current_price = float(trade["p"])

            # Try to get previous day's closing price from historical data
            # Get more historical data to ensure we have the actual previous trading day
            try:
                # Get 5 days of daily data to handle weekends/holidays
                prev_close_df = get_historical_bars_alpaca(ticker, "5d", "1d")

                if len(prev_close_df) >= 2:
                    # Get the second-to-last close (previous trading day)
                    # The last entry might be today's incomplete data
                    prev_close = prev_close_df.iloc[-2]["Close"]
                elif len(prev_close_df) >= 1:
                    # Fallback to last available close
                    prev_close = prev_close_df.iloc[-1]["Close"]
                else:
                    prev_close = current_price  # Fallback

            except Exception:
                # If historical data fails (e.g., 403), fallback to yfinance for accurate previous close
                try:
                    import yfinance as yf
                    stock = yf.Ticker(ticker)
                    info = stock.fast_info
                    prev_close = float(info.previous_close) if info.previous_close else current_price
                except Exception:
                    # Last resort: use current price as fallback
                    prev_close = current_price

            return {
                "price": current_price,
                "prev_close": prev_close,
                "change": current_price - prev_close,
                "change_pct": ((current_price - prev_close) / prev_close) * 100 if prev_close else 0,
            }
        except Exception as e:
            print(f"[ALPACA] Error fetching ticker info for {ticker}: {e}")
            return None

    cache_key = f"ticker_info_{ticker}"
    return get_cached_or_fetch(
        cache_key,
        _fetch_info,
        CACHE_TTL_QUOTE
    )
