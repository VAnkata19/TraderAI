"""
Graph state definition for the trading agent.
Flows through every node in the LangGraph.
"""

from typing import List, TypedDict


class GraphState(TypedDict):
    """
    Attributes:
        ticker:             The stock ticker being evaluated (e.g. "AAPL").
        news_documents:     Retrieved news documents from the news vector DB.
        chart_documents:    Retrieved chart / price documents from the chart vector DB.
        news_summary:       LLM-generated sentiment summary of the news.
        chart_summary:      LLM-generated technical summary of the chart data.
        portfolio_context:  Live Alpaca account, position & price data for the ticker.
        decision:           The trading decision: "buy", "sell", or "hold".
        quantity:           Number of shares the LLM chose to buy/sell (0 for hold).
        reasoning:          The LLM's explanation for its decision.
        actions_today:      How many buy/sell actions have been executed today.
        max_actions:        Maximum allowed actions per day.
        executed:           Whether the decision was actually executed (respects limit).
        order_result:       Summary of the Alpaca order that was placed (if any).
    """

    ticker: str
    news_documents: List[str]
    chart_documents: List[str]
    news_summary: str
    chart_summary: str
    portfolio_context: str
    decision: str          # "buy" | "sell" | "hold"
    quantity: int
    reasoning: str
    actions_today: int
    max_actions: int
    executed: bool
    order_result: str
