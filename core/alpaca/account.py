"""Account and positions queries for Alpaca."""

from typing import Any, Dict, List, Optional

import requests

from .client import get_headers, trading_url


def get_account() -> Dict[str, Any]:
    """Return Alpaca account info (equity, buying power, etc.)."""
    resp = requests.get(
        trading_url("/v2/account"),
        headers=get_headers(),
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def get_positions() -> List[Dict[str, Any]]:
    """Return all open positions."""
    resp = requests.get(
        trading_url("/v2/positions"),
        headers=get_headers(),
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def get_position(ticker: str) -> Optional[Dict[str, Any]]:
    """Return the open position for *ticker*, or None if not held."""
    try:
        resp = requests.get(
            trading_url(f"/v2/positions/{ticker}"),
            headers=get_headers(),
            timeout=10,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError:
        return None
