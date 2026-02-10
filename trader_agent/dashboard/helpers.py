"""
Shared helpers and state initialisation for the Streamlit dashboard.
Imported by every tab module and the main app.
"""

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests as _requests
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

# ── Project root ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent

from trader_agent.config import (
    CHART_INTERVAL,
    CHART_PERIOD,
    DISCORD_WEBHOOK_URL,
    LLM_MODEL,
    MAX_ACTIONS_PER_DAY,
    OPENAI_API_KEY,
    RUN_INTERVAL_SECONDS,
    TICKERS,
)

# ── Cost Estimation (for dashboard display) ─────────────────────────────────
# OpenAI pricing per 1M tokens (updated regularly)
OPENAI_PRICING = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-5.2": {"input": 2.00, "output": 8.00},
}

_DEFAULT_PRICING = {"input": 5.00, "output": 15.00}  # safe fallback

# Sample prompt to estimate token usage
SAMPLE_PROMPT = """
News Summary:
- Apple's Q4 earnings beat expectations with record revenue
- iPhone 16 sales surge in Asia markets
- New AI features announced for next generation devices

Chart Information:
- Current Price: $195.00
- 5-day high: $198.50
- 5-day low: $192.00
- 52-week high: $210.00
- Volume: 52M shares

Based on this information, should we BUY, SELL, or HOLD this stock?
Please provide reasoning in 2-3 sentences.
"""


def estimate_tokens(text: str, model: str = LLM_MODEL) -> tuple[int, int] | None:
    """
    Estimate input and output tokens using tiktoken.
    Returns (input_tokens, output_tokens) or None if tiktoken unavailable.
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        input_tokens = len(encoding.encode(text))
        # Estimate output: typically 1/10th to 1/5th of input for this type of task
        output_tokens = max(100, int(input_tokens * 0.15))
        return (input_tokens, output_tokens)
    except Exception:
        return None


def estimate_cost_per_cycle(model: str = LLM_MODEL) -> float:
    """Estimate cost in cents for one API call cycle using actual token counts."""
    # Use the provided model, fallback to configured LLM_MODEL, then gpt-4o
    if model not in OPENAI_PRICING:
        model = LLM_MODEL
    pricing = OPENAI_PRICING.get(model, _DEFAULT_PRICING)
    
    # Try to use actual token estimates
    token_estimate = estimate_tokens(SAMPLE_PROMPT, model)
    if token_estimate:
        input_tokens, output_tokens = token_estimate
    else:
        # Fallback: use conservative estimates if tiktoken unavailable
        input_tokens = 2500
        output_tokens = 200
    
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cents = (input_cost + output_cost) * 100
    return total_cents


def estimate_cost_per_day(model: str = LLM_MODEL) -> float:
    """Estimate cost in cents for full day (24 hours)."""
    cycles_per_day = (24 * 60 * 60) / RUN_INTERVAL_SECONDS
    cost_per_cycle = estimate_cost_per_cycle(model)
    return cost_per_cycle * cycles_per_day


# ── Persistent Storage ──────────────────────────────────────────────────────
_CUSTOM_TICKERS_FILE = ROOT / ".custom_tickers.json"
_DECISIONS_FILE = ROOT / ".decisions.json"
_ACTIONS_TODAY_FILE = ROOT / ".actions_today.json"


def load_custom_tickers() -> list[str]:
    if _CUSTOM_TICKERS_FILE.exists():
        try:
            with open(_CUSTOM_TICKERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_custom_tickers(tickers: list[str]) -> None:
    try:
        with open(_CUSTOM_TICKERS_FILE, "w") as f:
            json.dump(tickers, f)
    except Exception:
        pass


def load_decisions() -> list[dict]:
    if _DECISIONS_FILE.exists():
        try:
            with open(_DECISIONS_FILE, "r") as f:
                decisions = json.load(f)
                # Convert timestamp strings back to datetime objects
                for d in decisions:
                    if "timestamp" in d and isinstance(d["timestamp"], str):
                        d["timestamp"] = datetime.fromisoformat(
                            d["timestamp"]
                        )
                return decisions
        except Exception:
            return []
    return []


def save_decisions(decisions: list[dict]) -> None:
    try:
        # Convert datetime objects to ISO format strings for JSON serialization
        serializable = []
        for d in decisions:
            rec = d.copy()
            if "timestamp" in rec and hasattr(rec["timestamp"], "isoformat"):
                rec["timestamp"] = rec["timestamp"].isoformat()
            serializable.append(rec)
        with open(_DECISIONS_FILE, "w") as f:
            json.dump(serializable, f, indent=2)
    except Exception:
        pass


def load_actions_today() -> dict[str, int]:
    """Load actions_today from disk."""
    if _ACTIONS_TODAY_FILE.exists():
        try:
            with open(_ACTIONS_TODAY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_actions_today(actions: dict[str, int]) -> None:
    """Save actions_today to disk."""
    try:
        with open(_ACTIONS_TODAY_FILE, "w") as f:
            json.dump(actions, f, indent=2)
    except Exception:
        pass


# ── Validation Functions ────────────────────────────────────────────────────
def is_openai_valid() -> bool:
    """Check if OpenAI API key is valid by attempting to list models."""
    if not OPENAI_API_KEY:
        return False
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        _ = client.models.list()
        return True
    except Exception:
        return False


def is_discord_valid() -> bool:
    """Check if Discord webhook URL is valid."""
    if not DISCORD_WEBHOOK_URL:
        return False
    # Check URL format
    if not DISCORD_WEBHOOK_URL.startswith("https://discord.com/api/webhooks/"):
        return False
    return True


# ── Session State Initialisation ─────────────────────────────────────────────
def init_session_state() -> None:
    """Ensure all required session state keys exist."""
    if "decisions" not in st.session_state:
        st.session_state.decisions = load_decisions()
    if "actions_today" not in st.session_state or not isinstance(
        st.session_state.actions_today, dict
    ):
        st.session_state.actions_today = load_actions_today()
    if "current_day" not in st.session_state:
        st.session_state.current_day = datetime.now(timezone.utc).date()
    if "scheduler_process" not in st.session_state:
        st.session_state.scheduler_process = None
    if "custom_tickers" not in st.session_state:
        st.session_state.custom_tickers = load_custom_tickers()

    # Reset counters at midnight UTC
    now = datetime.now(timezone.utc)
    if now.date() != st.session_state.current_day:
        st.session_state.actions_today = {}
        st.session_state.current_day = now.date()


def get_all_tickers() -> list[str]:
    return TICKERS + [
        t for t in st.session_state.custom_tickers if t not in TICKERS
    ]


# ── Data Helpers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def search_yahoo_tickers(query: str) -> list[dict]:
    if not query or len(query) < 2:
        return []
    try:
        resp = _requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": query, "quotesCount": 8, "newsCount": 0},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        resp.raise_for_status()
        return [
            {
                "symbol": q.get("symbol", ""),
                "name": q.get("shortname")
                or q.get("longname")
                or q.get("symbol", ""),
                "type": q.get("quoteType", ""),
                "exchange": q.get("exchange", ""),
            }
            for q in resp.json().get("quotes", [])
            if q.get("symbol")
        ]
    except Exception:
        return []


@st.cache_data(ttl=60)
def get_ticker_data(
    ticker: str, period: str = "5d", interval: str = "5m"
) -> pd.DataFrame:
    return yf.Ticker(ticker).history(period=period, interval=interval)


@st.cache_data(ttl=60)
def get_ticker_info(ticker: str) -> dict | None:
    try:
        info = yf.Ticker(ticker).fast_info
        prev = info.previous_close
        last = info.last_price
        
        if last is None or prev is None:
            return None
            
        return {
            "price": last,
            "prev_close": prev,
            "change": last - prev,
            "change_pct": ((last - prev) / prev) * 100 if prev else 0,
        }
    except Exception:
        return None


def create_candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker} Price", "Volume"),
        row_heights=[0.7, 0.3],
    )
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="OHLC",
            increasing_line_color="#2ecc71",
            decreasing_line_color="#e74c3c",
        ),
        row=1,
        col=1,
    )
    bar_colors = [
        "#2ecc71" if row["Close"] >= row["Open"] else "#e74c3c"
        for _, row in df.iterrows()
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            marker_color=bar_colors,
            name="Volume",
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        showlegend=False,
    )
    return fig


# ── Module-level thread management (outside Streamlit session state) ────────
_analysis_threads: dict[str, threading.Thread] = {}
_analysis_stop_flags: dict[str, threading.Event] = {}
_last_run_time: dict[str, datetime] = {}


# ── Background Analysis Loop Threading ───────────────────────────────────────
def _run_analysis_loop(ticker: str, stop_flag: threading.Event) -> None:
    """
    Background thread function: runs analysis for ticker every 5 minutes until stopped.
    Uses only thread-safe parameters, no session_state access.
    """
    RUN_INTERVAL = 300  # 5 minutes
    
    while not stop_flag.is_set():
        try:
            # Import here to avoid circular imports
            from trader_agent.core.rss_fetcher import fetch_news_for_ticker
            from trader_agent.core.chart_fetcher import fetch_chart_for_ticker
            from trader_agent.core.ingestion import ingest_news, ingest_chart
            from trader_agent.graph.graph import app as graph_app
            from trader_agent.config import MAX_ACTIONS_PER_DAY
            
            _last_run_time[ticker] = datetime.now(timezone.utc)
            
            # Fetch news and chart
            news_docs = fetch_news_for_ticker(ticker)
            chart_docs = fetch_chart_for_ticker(ticker)
            
            # Deduplicate
            seen_news = set()
            deduped_news = []
            for doc in news_docs:
                h = hash(doc.page_content)
                if h not in seen_news:
                    seen_news.add(h)
                    deduped_news.append(doc)
            
            seen_chart = set()
            deduped_chart = []
            for doc in chart_docs:
                h = hash(doc.page_content)
                if h not in seen_chart:
                    seen_chart.add(h)
                    deduped_chart.append(doc)
            
            # Ingest
            ingest_news(deduped_news)
            ingest_chart(deduped_chart)
            
            # Load current state from disk
            decisions = load_decisions()
            actions_today = load_actions_today()
            _current_actions = actions_today.get(ticker, 0)
            
            # Run pipeline
            result = graph_app.invoke(
                {
                    "ticker": ticker,
                    "news_documents": [],
                    "chart_documents": [],
                    "news_summary": "",
                    "chart_summary": "",
                    "decision": "",
                    "reasoning": "",
                    "actions_today": _current_actions,
                    "max_actions": MAX_ACTIONS_PER_DAY,
                    "executed": False,
                }
            )
            
            # Update actions count
            if result.get("executed"):
                actions_today[ticker] = result["actions_today"]
                save_actions_today(actions_today)
            
            # Save decision
            decisions.insert(
                0,
                {
                    "timestamp": datetime.now(timezone.utc),
                    "ticker": ticker,
                    "decision": result.get("decision", "hold"),
                    "reasoning": result.get("reasoning", "")[:120] + "…",
                    "executed": result.get("executed", False),
                },
            )
            save_decisions(decisions)
            
            print(f"[LOOP] {ticker}: Analysis complete. Sleeping {RUN_INTERVAL}s…")
            
        except Exception as e:
            print(f"[LOOP] {ticker}: Error - {e}")
        
        # Wait 5 minutes (check stop flag every second)
        for _ in range(RUN_INTERVAL):
            if stop_flag.is_set():
                break
            time.sleep(1)


def start_analysis_loop(ticker: str) -> None:
    """Start a background analysis loop for the given ticker."""
    global _analysis_threads, _analysis_stop_flags
    
    if ticker not in _analysis_threads or _analysis_threads[ticker] is None:
        stop_flag = threading.Event()
        _analysis_stop_flags[ticker] = stop_flag
        
        thread = threading.Thread(
            target=_run_analysis_loop,
            args=(ticker, stop_flag),
            daemon=True,
        )
        _analysis_threads[ticker] = thread
        thread.start()
        print(f"[THREAD] Started analysis loop for {ticker}")


def stop_analysis_loop(ticker: str) -> None:
    """Stop the background analysis loop for the given ticker."""
    global _analysis_threads, _analysis_stop_flags
    
    if ticker in _analysis_stop_flags:
        _analysis_stop_flags[ticker].set()
    
    if ticker in _analysis_threads:
        thread = _analysis_threads[ticker]
        if thread and thread.is_alive():
            thread.join(timeout=2)
    
    _analysis_threads[ticker] = None
    print(f"[THREAD] Stopped analysis loop for {ticker}")


def is_analysis_loop_running(ticker: str) -> bool:
    """Check if analysis loop is running for the given ticker."""
    global _analysis_threads
    
    thread = _analysis_threads.get(ticker)
    return thread is not None and thread.is_alive()


def get_time_until_next_run(ticker: str) -> tuple[int, int]:
    """
    Get minutes and seconds until next analysis run.
    Returns (minutes, seconds).
    """
    global _last_run_time
    
    RUN_INTERVAL = 300  # 5 minutes
    
    if ticker not in _last_run_time:
        return (5, 0)
    
    last_run = _last_run_time[ticker]
    now = datetime.now(timezone.utc)
    elapsed = (now - last_run).total_seconds()
    remaining = max(0, RUN_INTERVAL - elapsed)
    
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    return (minutes, seconds)
