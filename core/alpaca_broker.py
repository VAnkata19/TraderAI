"""
DEPRECATED: This module has been split into core.alpaca.* submodules.

All imports still work for backward compatibility, but will redirect to the new location.

Migration guide:
  Old: from core.alpaca_broker import get_account
  New: from core.alpaca.account import get_account
  Also works: from core.alpaca import get_account

This deprecation wrapper will be removed in a future version.
"""

import warnings

# Emit deprecation warning on import
warnings.warn(
    "core.alpaca_broker is deprecated. Use core.alpaca instead. "
    "See core/alpaca_broker.py for migration guide.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from new location
from core.alpaca import (
    # Account
    get_account,
    get_positions,
    get_position,
    # Market data
    get_latest_quote,
    get_latest_trade,
    get_current_price,
    # Historical
    get_historical_bars_alpaca,
    get_current_price_cached,
    get_ticker_info_alpaca,
    # Orders
    submit_market_order,
    get_orders,
    get_fill_activity,
    # Portfolio
    build_portfolio_context,
    # Cache
    clear_alpaca_cache,
)

__all__ = [
    "get_account",
    "get_positions",
    "get_position",
    "get_latest_quote",
    "get_latest_trade",
    "get_current_price",
    "get_historical_bars_alpaca",
    "get_current_price_cached",
    "get_ticker_info_alpaca",
    "submit_market_order",
    "get_orders",
    "get_fill_activity",
    "build_portfolio_context",
    "clear_alpaca_cache",
]
