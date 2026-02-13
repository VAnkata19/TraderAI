"""Order execution and activity history for Alpaca."""

from typing import Any, Dict, List, Optional

import requests

from .client import get_headers, trading_url


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
        trading_url("/v2/orders"),
        headers=get_headers(),
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


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
        trading_url("/v2/orders"),
        headers=get_headers(),
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
        trading_url("/v2/account/activities/FILL"),
        headers=get_headers(),
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
