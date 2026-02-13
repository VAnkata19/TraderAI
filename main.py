"""
Main entry point for the Trading Agent.

• Continuously runs on a schedule (default every 5 minutes).
• Each cycle:  fetch RSS news → ingest into news vector DB
                fetch chart data → ingest into chart vector DB
                run the LangGraph pipeline for each ticker
• Tracks daily action budget (resets at midnight UTC).
"""

import sys
from pathlib import Path

# Ensure the package root is importable when launched as a script
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import time
from datetime import datetime, timezone

from config import (
    MAX_ACTIONS_PER_DAY,
    RUN_INTERVAL_SECONDS,
)
from core.rss_fetcher import fetch_news_for_ticker
from core.chart_fetcher import fetch_chart_for_ticker
from core.ingestion import ingest_news, ingest_chart
from dashboard.helpers import load_actions_today, save_actions_today, load_tickers
from graph.graph import app


def run_cycle(tickers: list[str], actions_today: dict[str, int]) -> dict[str, int]:
    """
    Run one full cycle for all tickers.
    *actions_today* is a per-ticker dict: {"AAPL": 2, "MSFT": 0, …}.
    Returns the updated dict.
    """
    # ── 1. Ingest fresh data ─────────────────────────────────────────────
    for ticker in tickers:
        news_docs = fetch_news_for_ticker(ticker)
        ingest_news(news_docs)

        chart_docs = fetch_chart_for_ticker(ticker)
        ingest_chart(chart_docs)

    # ── 2. Run the trading graph for each ticker ─────────────────────────
    for ticker in tickers:
        ticker_actions = actions_today.get(ticker, 0)
        budget_str = "unlimited" if MAX_ACTIONS_PER_DAY == -1 else str(MAX_ACTIONS_PER_DAY)
        print(f"\n{'='*60}")
        print(f"  Processing {ticker}  |  Actions today: {ticker_actions}/{budget_str}")
        print(f"{'='*60}")

        result = app.invoke(
            {
                "ticker": ticker,
                "news_documents": [],
                "chart_documents": [],
                "news_summary": "",
                "chart_summary": "",
                "portfolio_context": "",
                "decision": "",
                "quantity": 0,
                "reasoning": "",
                "actions_today": ticker_actions,
                "max_actions": MAX_ACTIONS_PER_DAY,
                "executed": False,
                "order_result": "",
            }
        )

        # Update the per-ticker action counter if an action was executed
        if result.get("executed"):
            actions_today[ticker] = result["actions_today"]

        print(f"  → {ticker}: {result['decision'].upper()} | Executed: {result['executed']}")

    return actions_today


def main() -> None:
    tickers = load_tickers()  # Load tickers from file
    print("🚀 Trading Agent started")
    print(f"   Tickers: {', '.join(tickers)}")
    print(f"   Max actions/day/stock: {'unlimited' if MAX_ACTIONS_PER_DAY == -1 else MAX_ACTIONS_PER_DAY}")
    print(f"   Run interval: {RUN_INTERVAL_SECONDS}s")
    print()

    actions_today = load_actions_today()  # shared with dashboard via disk

    while True:
        now = datetime.now(timezone.utc)

        # Reload from disk each cycle — load_actions_today() auto-resets on new day
        actions_today = load_actions_today()

        print(f"\n⏰ Cycle start: {now.isoformat()}")

        try:
            actions_today = run_cycle(tickers, actions_today)
            save_actions_today(actions_today)
        except Exception as exc:
            print(f"❌ Cycle failed: {exc}")

        print(f"\n💤 Sleeping {RUN_INTERVAL_SECONDS}s until next cycle…")
        time.sleep(RUN_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
