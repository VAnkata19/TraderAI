"""Portfolio context builder for LLM trading decisions."""

from typing import Callable, Optional

from graph.context.base import ContextBuilder
from graph.context.formatters import (
    format_account_summary,
    format_error_message,
    format_no_position,
    format_price_info,
    format_position_summary,
)


class PortfolioContextBuilder(ContextBuilder):
    """Build portfolio context combining account, positions, and price data.

    Fetches current account state, position details, and price information,
    then formats them into a natural language string for LLM consumption.
    """

    def __init__(
        self,
        get_account: Callable,
        get_position: Callable,
        get_price: Callable,
    ):
        """Initialize with dependency-injected data fetchers.

        Args:
            get_account: Function that returns account dict
            get_position: Function that takes ticker and returns position dict or None
            get_price: Function that takes ticker and returns current price float
        """
        self._get_account = get_account
        self._get_position = get_position
        self._get_price = get_price

    def build(self, ticker: str) -> str:
        """Build portfolio context string for a ticker.

        Combines account summary, current position (if any), and price information
        into a comprehensive portfolio context. Gracefully handles failures for each component.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Formatted portfolio context string
        """
        lines = []

        # 1. Account info
        try:
            account = self._get_account()
            lines.append(format_account_summary(account))
        except Exception as e:
            lines.append(format_error_message("Account info", e))

        # 2. Current price
        try:
            price = self._get_price(ticker)
            lines.append(format_price_info(ticker, price))
        except Exception as e:
            lines.append(format_error_message("Current price", e))

        # 3. Position details (if any)
        try:
            position = self._get_position(ticker)
            if position:
                lines.append(format_position_summary(ticker, position))
            else:
                lines.append(format_no_position(ticker))
        except Exception as e:
            lines.append(format_error_message("Position info", e))

        return "\n".join(lines)


def create_portfolio_context_builder() -> PortfolioContextBuilder:
    """Factory function to create a portfolio context builder with default dependencies.

    Returns:
        PortfolioContextBuilder configured with core.alpaca functions
    """
    from core.alpaca import get_account, get_current_price, get_position

    return PortfolioContextBuilder(
        get_account=get_account,
        get_position=lambda ticker: get_position(ticker),  # Adapt to required signature
        get_price=get_current_price,
    )
