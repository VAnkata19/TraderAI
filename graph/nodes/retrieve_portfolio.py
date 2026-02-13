"""
Node: Retrieve live portfolio & price data from Alpaca for the current ticker.

Uses the separated PortfolioContextBuilder for clean separation between
data fetching and context formatting.
"""

from typing import Any, Dict

from graph.state import GraphState
from graph.context import create_portfolio_context_builder


# Build context builder once at module load
_context_builder = create_portfolio_context_builder()


def retrieve_portfolio(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE PORTFOLIO---")
    ticker = state["ticker"]

    try:
        context = _context_builder.build(ticker)
        print(f"[PORTFOLIO] Successfully retrieved portfolio context for {ticker}")
    except Exception as e:
        context = f"Portfolio/price data unavailable: {e}"
        print(f"[PORTFOLIO] ⚠️  Failed to retrieve portfolio context: {e}")

    return {"portfolio_context": context}
