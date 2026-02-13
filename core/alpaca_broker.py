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
from typing import Any, Dict, List, Optional

import requests

from config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    ALPACA_BASE_URL,
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
