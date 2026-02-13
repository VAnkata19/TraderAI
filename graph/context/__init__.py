"""LLM context building - separates data fetching from prompt engineering."""

from .base import ContextBuilder
from .portfolio import PortfolioContextBuilder, create_portfolio_context_builder
from .formatters import (
    format_account_summary,
    format_position_summary,
    format_price_info,
    format_no_position,
    format_error_message,
)

__all__ = [
    # Base interface
    "ContextBuilder",
    # Implementations
    "PortfolioContextBuilder",
    # Factory
    "create_portfolio_context_builder",
    # Formatters
    "format_account_summary",
    "format_position_summary",
    "format_price_info",
    "format_no_position",
    "format_error_message",
]
