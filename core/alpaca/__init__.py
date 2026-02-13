"""
Alpaca broker integration - refactored into focused submodules.

All functions are re-exported from this __init__.py for backward compatibility.

Migration guide:
  Old: from core.alpaca_broker import get_account
  New: from core.alpaca.account import get_account
  Also works: from core.alpaca import get_account
"""

from .account import get_account, get_positions, get_position
from .market_data import get_latest_quote, get_latest_trade, get_current_price
from .historical import (
    get_historical_bars_alpaca,
    get_current_price_cached,
    get_ticker_info_alpaca,
)
from .orders import submit_market_order, get_orders, get_fill_activity
from .portfolio import build_portfolio_context
from .cache import clear_alpaca_cache

__all__ = [
    # Account
    "get_account",
    "get_positions",
    "get_position",
    # Market data
    "get_latest_quote",
    "get_latest_trade",
    "get_current_price",
    # Historical
    "get_historical_bars_alpaca",
    "get_current_price_cached",
    "get_ticker_info_alpaca",
    # Orders
    "submit_market_order",
    "get_orders",
    "get_fill_activity",
    # Portfolio
    "build_portfolio_context",
    # Cache
    "clear_alpaca_cache",
]
