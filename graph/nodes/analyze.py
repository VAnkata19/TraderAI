"""
Node: Run news-sentiment and chart-technical analysis in parallel, then produce a
      trading decision (buy / sell / hold).

Uses ChainOrchestrator for concurrent execution with timeout handling.
"""

from typing import Any, Dict

from graph.state import GraphState
from graph.orchestrator import ChainOrchestrator, ChainExecutionConfig
from graph.chains import ChainFactory, TradingDecision

# Build chains and orchestrator once at module load
_chains = ChainFactory.build_all_chains()
_orchestrator = ChainOrchestrator(default_timeout=30.0)


def analyze(state: GraphState) -> Dict[str, Any]:
    print("---ANALYZE---")
    ticker = state["ticker"]
    news_docs = state["news_documents"]
    chart_docs = state["chart_documents"]
    portfolio_context = state.get("portfolio_context", "No portfolio data available.")
    actions_today = state["actions_today"]
    max_actions = state["max_actions"]

    # ── Phase 1: Parallel execution of news + chart analysis ──────────────────
    # These are independent and can run concurrently for ~33% performance gain
    parallel_chains = [
        (
            ChainExecutionConfig(
                name="news_summary",
                timeout=30.0,
                fallback_value="Unable to retrieve news sentiment (timeout). Proceeding with neutral assumption.",
                required=False,
            ),
            _chains["news_sentiment"],
            {
                "ticker": ticker,
                "news_documents": "\n\n---\n\n".join(news_docs) if news_docs else "No recent news available.",
            },
        ),
        (
            ChainExecutionConfig(
                name="chart_summary",
                timeout=30.0,
                fallback_value="Unable to retrieve chart analysis (timeout). Proceeding with neutral assumption.",
                required=False,
            ),
            _chains["chart_analysis"],
            {
                "ticker": ticker,
                "chart_documents": "\n\n---\n\n".join(chart_docs) if chart_docs else "No chart data available.",
            },
        ),
    ]

    summaries = _orchestrator.execute_parallel(parallel_chains)
    news_summary = summaries["news_summary"]
    chart_summary = summaries["chart_summary"]

    # ── Phase 2: Trading decision (depends on summaries) ────────────────────────
    # This must run sequentially after summaries are ready
    decision_chains = [
        (
            ChainExecutionConfig(
                name="decision",
                timeout=30.0,
                fallback_value=TradingDecision(
                    decision="hold",
                    reasoning="Unable to reach decision due to timeout or error. Defaulting to HOLD.",
                    quantity=0,
                    confidence=0.3,
                ),
                required=False,
            ),
            _chains["trading_decision"],
            {
                "ticker": ticker,
                "news_summary": news_summary,
                "chart_summary": chart_summary,
                "portfolio_context": portfolio_context,
                "actions_today": actions_today,
                "max_actions": max_actions,
            },
        ),
    ]

    decision_result = _orchestrator.execute_sequential(decision_chains)
    result = decision_result["decision"]

    print(f"[ANALYZE] Decision: {result.decision} (confidence: {result.confidence:.2f})")

    return {
        "news_summary": news_summary,
        "chart_summary": chart_summary,
        "decision": result.decision,
        "quantity": result.quantity,
        "reasoning": result.reasoning,
    }
