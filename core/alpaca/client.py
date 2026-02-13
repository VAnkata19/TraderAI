"""HTTP client infrastructure for Alpaca API."""

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

# Data API base (works for both paper and live)
_DATA_URL = "https://data.alpaca.markets"


def get_headers() -> dict:
    """Return HTTP headers with Alpaca API credentials."""
    return {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type": "application/json",
    }


def trading_url(path: str) -> str:
    """Build URL for trading API endpoint."""
    return f"{ALPACA_BASE_URL}{path}"


def data_url(path: str) -> str:
    """Build URL for data API endpoint."""
    return f"{_DATA_URL}{path}"
