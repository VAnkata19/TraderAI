"""Real-time market data queries for Alpaca."""

from typing import Any, Dict

import requests

from .client import get_headers, data_url


def get_latest_quote(ticker: str) -> Dict[str, Any]:
    """
    Get the latest quote (bid/ask) for *ticker* from Alpaca's data API.
    Returns dict with keys like 'ap' (ask price), 'bp' (bid price), etc.
    """
    resp = requests.get(
        data_url(f"/v2/stocks/{ticker}/quotes/latest"),
        headers=get_headers(),
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
        data_url(f"/v2/stocks/{ticker}/trades/latest"),
        headers=get_headers(),
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
