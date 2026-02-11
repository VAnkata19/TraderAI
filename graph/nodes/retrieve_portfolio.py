"""
Node: Retrieve live portfolio & price data from Alpaca for the current ticker.
"""

from typing import Any, Dict

from graph.state import GraphState
from core.alpaca_broker import build_portfolio_context


def retrieve_portfolio(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE PORTFOLIO---")
    ticker = state["ticker"]

    try:
        context = build_portfolio_context(ticker)
        print(f"[PORTFOLIO] Successfully retrieved Alpaca data for {ticker}")
    except Exception as e:
        context = f"Portfolio/price data unavailable: {e}"
        print(f"[PORTFOLIO] ⚠️  Failed to retrieve Alpaca data: {e}")

    return {"portfolio_context": context}
