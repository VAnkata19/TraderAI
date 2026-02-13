"""Cache configuration: TTL constants for different data types."""

from datetime import timedelta

# Real-time market data (very volatile, frequent updates)
CACHE_TTL_QUOTE = timedelta(seconds=30)
CACHE_TTL_LATEST_TRADE = timedelta(seconds=30)

# Account and position data (less volatile, but important for trading decisions)
CACHE_TTL_ACCOUNT = timedelta(seconds=30)
CACHE_TTL_POSITIONS = timedelta(seconds=60)

# Historical market data (relatively stable, rarely changes)
CACHE_TTL_HISTORICAL = timedelta(seconds=300)  # 5 minutes

# Ticker info (company info, fairly static)
CACHE_TTL_TICKER_INFO = timedelta(seconds=3600)  # 1 hour

# Order history (updates when new orders placed)
CACHE_TTL_ORDERS = timedelta(seconds=60)

# Fill activity (updates when orders fill)
CACHE_TTL_FILL_ACTIVITY = timedelta(seconds=60)
