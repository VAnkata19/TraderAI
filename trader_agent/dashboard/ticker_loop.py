"""
Per-ticker analysis loop runner.

Usage:
    python -m trader_agent.dashboard.ticker_loop AAPL
    python -m trader_agent.dashboard.ticker_loop MSFT

Runs the full analysis pipeline for a single ticker in a continuous loop
with a configurable interval (default 5 min). Designed to be launched as
a subprocess from the Streamlit dashboard.
"""

import atexit
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Ensure imports work when invoked as a subprocess
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

from trader_agent.config import RUN_INTERVAL_SECONDS, MAX_ACTIONS_PER_DAY
from trader_agent.core.rss_fetcher import fetch_news_for_ticker
from trader_agent.core.chart_fetcher import fetch_chart_for_ticker
from trader_agent.core.ingestion import ingest_news, ingest_chart
from trader_agent.graph.graph import app

# ── PID-file helpers ─────────────────────────────────────────────────────────
_PIDS_DIR = _ROOT / ".pids"
_DECISIONS_FILE = _ROOT / ".decisions.json"


def _pid_file(ticker: str) -> Path:
    return _PIDS_DIR / ticker


def _write_pid(ticker: str) -> None:
    _PIDS_DIR.mkdir(exist_ok=True)
    _pid_file(ticker).write_text(str(os.getpid()))


def _remove_pid(ticker: str) -> None:
    try:
        _pid_file(ticker).unlink(missing_ok=True)
    except Exception:
        pass


def _save_decision(ticker: str, result: dict) -> None:
    """Append a decision to the shared .decisions.json file."""
    try:
        decisions = []
        if _DECISIONS_FILE.exists():
            with open(_DECISIONS_FILE, "r") as f:
                decisions = json.load(f)

        decisions.insert(0, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticker": ticker,
            "decision": result["decision"],
            "reasoning": result.get("reasoning", "")[:120] + "…",
            "executed": result["executed"],
        })

        with open(_DECISIONS_FILE, "w") as f:
            json.dump(decisions, f, indent=2)
    except Exception as exc:
        print(f"[{ticker}] Failed to save decision: {exc}", flush=True)


def run_ticker_loop(ticker: str) -> None:
    """Run analysis for *ticker* in an infinite loop."""

    # Write PID file so the dashboard knows we're alive
    _write_pid(ticker)
    atexit.register(_remove_pid, ticker)

    # Also clean up on SIGTERM (what the dashboard sends to stop us)
    def _handle_term(signum, frame):
        _remove_pid(ticker)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_term)

    print(f"🚀 Starting loop for {ticker} (pid {os.getpid()})", flush=True)
    print(f"   Interval: {RUN_INTERVAL_SECONDS}s", flush=True)
    print(f"   Max actions/day: {MAX_ACTIONS_PER_DAY}", flush=True)

    actions_today = 0
    current_day = datetime.now(timezone.utc).date()

    while True:
        now = datetime.now(timezone.utc)

        # Reset action counter at midnight UTC
        if now.date() != current_day:
            print(f"🔄 New day – resetting action counter for {ticker}", flush=True)
            actions_today = 0
            current_day = now.date()

        print(f"\n⏰ [{ticker}] Cycle start: {now.isoformat()}", flush=True)

        try:
            # 1 — Fetch & ingest news
            try:
                news_docs = fetch_news_for_ticker(ticker)
                ingest_news(news_docs)
            except Exception as e:
                print(f"⚠️  [{ticker}] Failed to fetch/ingest news: {e}", flush=True)
                news_docs = []

            # 2 — Fetch & ingest chart
            try:
                chart_docs = fetch_chart_for_ticker(ticker)
                ingest_chart(chart_docs)
            except Exception as e:
                print(f"⚠️  [{ticker}] Failed to fetch/ingest chart: {e}", flush=True)
                chart_docs = []

            # 3 — Run the LangGraph pipeline with timeout
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        app.invoke,
                        {
                            "ticker": ticker,
                            "news_documents": [],
                            "chart_documents": [],
                            "news_summary": "",
                            "chart_summary": "",
                            "decision": "",
                            "reasoning": "",
                            "actions_today": actions_today,
                            "max_actions": MAX_ACTIONS_PER_DAY,
                            "executed": False,
                        }
                    )
                    # 120 second timeout for the entire pipeline
                    result = future.result(timeout=120)
            except FuturesTimeoutError:
                print(f"⏱️  [{ticker}] Pipeline timeout exceeded (>120s)", flush=True)
                result = {
                    "ticker": ticker,
                    "decision": "hold",
                    "reasoning": "Pipeline timeout, defaulting to HOLD",
                    "executed": False,
                    "actions_today": actions_today,
                }
            except Exception as e:
                print(f"❌ [{ticker}] Pipeline error: {e}", flush=True)
                import traceback
                traceback.print_exc(file=__import__('sys').stdout)
                result = {
                    "ticker": ticker,
                    "decision": "hold",
                    "reasoning": f"Pipeline failed: {str(e)[:50]}, defaulting to HOLD",
                    "executed": False,
                    "actions_today": actions_today,
                }

            if result.get("executed"):
                actions_today = result["actions_today"]

            decision = result["decision"].upper()
            executed = result["executed"]
            print(f"✅ [{ticker}] {decision} | Executed: {executed} | Actions: {actions_today}/{MAX_ACTIONS_PER_DAY}", flush=True)

            # 4 — Persist the decision so the dashboard can display it
            _save_decision(ticker, result)

        except Exception as exc:
            print(f"❌ [{ticker}] Unexpected cycle error: {exc}", flush=True)
            import traceback
            traceback.print_exc(file=__import__('sys').stdout)

        print(f"💤 [{ticker}] Sleeping {RUN_INTERVAL_SECONDS}s…", flush=True)
        time.sleep(RUN_INTERVAL_SECONDS)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m trader_agent.dashboard.ticker_loop <TICKER>")
        sys.exit(1)

    run_ticker_loop(sys.argv[1])
