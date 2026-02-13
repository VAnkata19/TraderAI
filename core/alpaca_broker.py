"""
Alpaca paper-trading broker integration.

Provides helpers to:
  • get current stock price / quote
  • get account info (buying power, equity, etc.)
  • get current positions & P/L
  • submit market BUY / SELL orders
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    ALPACA_BASE_URL,
    ALPACA_RATE_LIMIT_PER_MINUTE,
    ALPACA_HISTORICAL_CACHE_SECONDS,
    ALPACA_QUOTE_CACHE_SECONDS,
)

# ── HTTP helpers ─────────────────────────────────────────────────────────────

_HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
    "Content-Type": "application/json",
}

# Data API base (works for both paper and live)
_DATA_URL = "https://data.alpaca.markets"


def _trading_url(path: str) -> str:
    return f"{ALPACA_BASE_URL}{path}"


def _data_url(path: str) -> str:
    return f"{_DATA_URL}{path}"


# ── Account & positions ─────────────────────────────────────────────────────

def get_account() -> Dict[str, Any]:
    """Return Alpaca account info (equity, buying power, etc.)."""
    resp = requests.get(_trading_url("/v2/account"), headers=_HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_positions() -> List[Dict[str, Any]]:
    """Return all open positions."""
    resp = requests.get(_trading_url("/v2/positions"), headers=_HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_position(ticker: str) -> Optional[Dict[str, Any]]:
    """Return the open position for *ticker*, or None if not held."""
    try:
        resp = requests.get(
            _trading_url(f"/v2/positions/{ticker}"),
            headers=_HEADERS,
            timeout=10,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError:
        return None


# ── Market data ──────────────────────────────────────────────────────────────

def get_latest_quote(ticker: str) -> Dict[str, Any]:
    """
    Get the latest quote (bid/ask) for *ticker* from Alpaca's data API.
    Returns dict with keys like 'ap' (ask price), 'bp' (bid price), etc.
    """
    resp = requests.get(
        _data_url(f"/v2/stocks/{ticker}/quotes/latest"),
        headers=_HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("quote", resp.json())


def get_latest_trade(ticker: str) -> Dict[str, Any]:
    """
    Get the latest trade for *ticker*.
    Returns dict with 'p' (price), 's' (size), etc.
    """
    resp = requests.get(
        _data_url(f"/v2/stocks/{ticker}/trades/latest"),
        headers=_HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("trade", resp.json())


def get_current_price(ticker: str) -> float:
    """Best-effort current price: last trade price, falling back to mid-quote."""
    try:
        trade = get_latest_trade(ticker)
        return float(trade["p"])
    except Exception:
        quote = get_latest_quote(ticker)
        return (float(quote["bp"]) + float(quote["ap"])) / 2


# ── Data caching and rate limiting ──────────────────────────────────────────


class AlpacaDataCache:
    """
    Simple in-memory cache for Alpaca market data with rate limiting.
    Helps manage the 200 calls/minute limit on free plan.
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._request_times: List[float] = []

    def _is_rate_limited(self) -> bool:
        """Check if we're approaching the rate limit."""
        now = time.time()
        # Remove requests older than 1 minute
        self._request_times = [t for t in self._request_times if now - t < 60]
        return len(self._request_times) >= ALPACA_RATE_LIMIT_PER_MINUTE

    def _record_request(self):
        """Record a new API request timestamp."""
        self._request_times.append(time.time())

    def get_cached_or_fetch(self, key: str, fetch_fn, cache_seconds: int):
        """Get cached data or fetch if expired/missing."""
        now = time.time()
        
        if key in self._cache:
            cached_data = self._cache[key]
            if now - cached_data["timestamp"] < cache_seconds:
                return cached_data["data"]
        
        # Check rate limiting before making request
        if self._is_rate_limited():
            print(f"[ALPACA] Rate limit approached ({len(self._request_times)} requests in last minute)")
            if key in self._cache:
                print(f"[ALPACA] Returning stale cache for {key}")
                return self._cache[key]["data"]
            raise Exception("Rate limited and no cached data available")
        
        # Fetch new data
        self._record_request()
        data = fetch_fn()
        self._cache[key] = {"data": data, "timestamp": now}
        return data


# Global cache instance
_data_cache = AlpacaDataCache()


# ── Historical market data ─────────────────────────────────────────────────


def _convert_period_to_dates(period: str, interval: str) -> tuple[str, str]:
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
            _data_url("/v2/stocks/bars"),
            headers=_HEADERS,
            params=params,
            timeout=10,
        )
        
        if resp.status_code == 403:
            raise Exception(f"Alpaca API access denied (403). Free plan may have limited access to historical data. Status: {resp.status_code}")
        
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
    return _data_cache.get_cached_or_fetch(
        cache_key, 
        _fetch_bars, 
        ALPACA_HISTORICAL_CACHE_SECONDS
    )


def get_current_price_cached(ticker: str) -> float:
    """Get current price with caching to reduce API calls."""
    
    def _fetch_price():
        return get_current_price(ticker)
    
    cache_key = f"price_{ticker}"
    return _data_cache.get_cached_or_fetch(
        cache_key,
        _fetch_price,
        ALPACA_QUOTE_CACHE_SECONDS
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
            # If historical data is restricted, use current price as fallback
            try:
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                prev_close_df = get_historical_bars_alpaca(ticker, "2d", "1d")
                
                if len(prev_close_df) >= 1:
                    prev_close = prev_close_df.iloc[-1]["Close"]
                else:
                    prev_close = current_price  # Fallback
            except Exception:
                # If historical data fails (e.g., 403), estimate from quote spread
                quote = get_latest_quote(ticker)
                prev_close = (float(quote["bp"]) + float(quote["ap"])) / 2
            
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
    return _data_cache.get_cached_or_fetch(
        cache_key,
        _fetch_info, 
        ALPACA_QUOTE_CACHE_SECONDS
    )


# ── Order execution ─────────────────────────────────────────────────────────

def submit_market_order(
    ticker: str,
    qty: int,
    side: str,  # "buy" or "sell"
) -> Dict[str, Any]:
    """
    Submit a market order on Alpaca paper trading.

    Parameters
    ----------
    ticker : str  – stock symbol, e.g. "AAPL"
    qty    : int  – number of shares
    side   : str  – "buy" or "sell"

    Returns
    -------
    dict  – the Alpaca order object
    """
    payload = {
        "symbol": ticker,
        "qty": str(qty),
        "side": side,
        "type": "market",
        "time_in_force": "day",
    }
    resp = requests.post(
        _trading_url("/v2/orders"),
        headers=_HEADERS,
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ── Order & activity history ─────────────────────────────────────────────────

def get_orders(
    status: str = "all",
    limit: int = 100,
    direction: str = "desc",
    symbols: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List recent orders from Alpaca.

    Parameters
    ----------
    status    : "open", "closed", or "all"
    limit     : max results (up to 500)
    direction : "asc" or "desc"
    symbols   : comma-separated ticker filter, e.g. "AAPL,MSFT"
    """
    params: Dict[str, Any] = {
        "status": status,
        "limit": limit,
        "direction": direction,
    }
    if symbols:
        params["symbols"] = symbols
    resp = requests.get(
        _trading_url("/v2/orders"),
        headers=_HEADERS,
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_fill_activity(
    limit: int = 100,
    direction: str = "desc",
) -> List[Dict[str, Any]]:
    """
    Get recent FILL activities from Alpaca account activities.

    Returns list of fill dicts with keys like 'symbol', 'side', 'qty',
    'price', 'transaction_time', 'order_id', etc.
    """
    params: Dict[str, Any] = {
        "direction": direction,
        "page_size": limit,
    }
    resp = requests.get(
        _trading_url("/v2/account/activities/FILL"),
        headers=_HEADERS,
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ── Convenience: build a context string for the LLM ─────────────────────────

def build_portfolio_context(ticker: str) -> str:
    """
    Build a human-readable summary of the Alpaca account, current position
    in *ticker*, and its live price – ready to inject into the LLM prompt.
    """
    lines: list[str] = []

    try:
        acct = get_account()
        lines.append(
            f"Account equity: ${float(acct['equity']):,.2f}  |  "
            f"Buying power: ${float(acct['buying_power']):,.2f}  |  "
            f"Cash: ${float(acct['cash']):,.2f}"
        )
    except Exception as e:
        lines.append(f"Account info unavailable: {e}")

    try:
        price = get_current_price(ticker)
        lines.append(f"Current price of {ticker}: ${price:,.2f}")
    except Exception as e:
        lines.append(f"Current price unavailable: {e}")

    try:
        pos = get_position(ticker)
        if pos:
            qty = float(pos["qty"])
            avg_entry = float(pos["avg_entry_price"])
            market_value = float(pos["market_value"])
            unrealised_pl = float(pos["unrealized_pl"])
            unrealised_pct = float(pos["unrealized_plpc"]) * 100
            lines.append(
                f"Current position in {ticker}: {qty:.0f} shares @ avg ${avg_entry:,.2f}  |  "
                f"Market value: ${market_value:,.2f}  |  "
                f"Unrealised P/L: ${unrealised_pl:,.2f} ({unrealised_pct:+.2f}%)"
            )
        else:
            lines.append(f"No open position in {ticker}.")
    except Exception as e:
        lines.append(f"Position info unavailable: {e}")

    # Also list all positions briefly
    try:
        all_positions = get_positions()
        if all_positions:
            pos_strs = []
            for p in all_positions:
                sym = p["symbol"]
                q = float(p["qty"])
                upl = float(p["unrealized_pl"])
                pos_strs.append(f"{sym}: {q:.0f} shares (P/L ${upl:,.2f})")
            lines.append(f"All positions: {' | '.join(pos_strs)}")
        else:
            lines.append("Portfolio is empty – no open positions.")
    except Exception as e:
        lines.append(f"Positions list unavailable: {e}")

    return "\n".join(lines)
