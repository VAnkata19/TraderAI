"""Formatting helpers for converting data to LLM-friendly text."""

from typing import Any, Dict, Optional


def format_account_summary(account: Dict[str, Any]) -> str:
    """Format account data into readable text for LLM.

    Args:
        account: Account dict with keys: equity, buying_power, cash, etc.

    Returns:
        Formatted account summary string
    """
    equity = float(account.get("equity", 0))
    buying_power = float(account.get("buying_power", 0))
    cash = float(account.get("cash", 0))

    return (
        f"Account equity: ${equity:,.2f}  |  "
        f"Buying power: ${buying_power:,.2f}  |  "
        f"Cash: ${cash:,.2f}"
    )


def format_position_summary(ticker: str, position: Dict[str, Any]) -> str:
    """Format position data into readable text for LLM.

    Args:
        ticker: Stock ticker symbol
        position: Position dict with keys: qty, avg_entry_price, market_value, unrealized_pl, unrealized_plpc

    Returns:
        Formatted position summary string
    """
    qty = float(position.get("qty", 0))
    avg_entry = float(position.get("avg_entry_price", 0))
    market_value = float(position.get("market_value", 0))
    unrealised_pl = float(position.get("unrealized_pl", 0))
    unrealised_pct = float(position.get("unrealized_plpc", 0)) * 100

    return (
        f"Current position in {ticker}: {qty:.0f} shares @ avg ${avg_entry:,.2f}  |  "
        f"Market value: ${market_value:,.2f}  |  "
        f"Unrealised P/L: ${unrealised_pl:,.2f} ({unrealised_pct:+.2f}%)"
    )


def format_price_info(ticker: str, price: float) -> str:
    """Format current price info into readable text for LLM.

    Args:
        ticker: Stock ticker symbol
        price: Current price in dollars

    Returns:
        Formatted price string
    """
    return f"Current price of {ticker}: ${price:,.2f}"


def format_no_position(ticker: str) -> str:
    """Format message for no open position.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Message string
    """
    return f"No open position in {ticker}."


def format_error_message(context_type: str, error: Optional[Exception] = None) -> str:
    """Format error message for context building failure.

    Args:
        context_type: Type of context that failed (e.g., "Account info", "Position data")
        error: Optional exception that caused the failure

    Returns:
        Error message string
    """
    if error:
        return f"{context_type} unavailable: {error}"
    return f"{context_type} unavailable."
