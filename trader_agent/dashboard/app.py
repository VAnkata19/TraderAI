"""
TraderAI — Streamlit Dashboard
===============================
Slim coordinator that wires the sidebar, tabs, and shared state.

Run with:
    streamlit run trader_agent/dashboard/app.py
"""

import sys
from pathlib import Path

# Ensure the package root is importable when launched with `streamlit run`
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from trader_agent.config import (
    TICKERS,
    MAX_ACTIONS_PER_DAY,
    RUN_INTERVAL_SECONDS,
    LLM_MODEL,
    DISCORD_WEBHOOK_URL,
    OPENAI_API_KEY,
    CHART_PERIOD,
    CHART_INTERVAL,
)
from trader_agent.dashboard.helpers import (
    init_session_state,
    get_all_tickers,
    search_yahoo_tickers,
    save_custom_tickers,
    is_openai_valid,
    is_discord_valid,
    estimate_cost_per_cycle,
    estimate_cost_per_day,
)

# Tab modules
from trader_agent.dashboard.tabs import (
    tab_stocks,
    tab_dashboard,
    tab_analysis,
    tab_news,
    tab_charts,
    tab_pipeline,
)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TraderAI Dashboard",
    page_icon="�",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
    div[data-testid="stMetric"] {
        background-color: rgba(30, 30, 46, 0.6);
        border: 1px solid rgba(49, 50, 68, 0.6);
        padding: 12px 16px;
        border-radius: 8px;
    }
    .decision-buy  { color: #2ecc71; font-weight: 700; font-size: 1.5rem; }
    .decision-sell { color: #e74c3c; font-weight: 700; font-size: 1.5rem; }
    .decision-hold { color: #f39c12; font-weight: 700; font-size: 1.5rem; }
    .pipeline-step {
        padding: 14px 18px;
        border-radius: 8px;
        border-left: 4px solid #3498db;
        margin-bottom: 12px;
    }
    /* Status checkboxes styling - override disabled greyed out */
    input[type="checkbox"]:disabled {
        opacity: 1 !important;
    }
    input[type="checkbox"]:disabled + label {
        color: #ffffff !important;
        opacity: 1 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ── Session State ────────────────────────────────────────────────────────────
init_session_state()

all_tickers = get_all_tickers()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# TraderAI")
    st.caption("LLM-powered trading agent")
    st.divider()

    selected_ticker = st.selectbox("Active Ticker", all_tickers)

    # ── Ticker search ────────────────────────────────────────────────
    with st.expander("Add Ticker", expanded=False):
        search_query = st.text_input(
            "Search by name or symbol",
            placeholder="e.g. nvidia, TSLA, apple…",
            key="ticker_search",
        )
        if search_query:
            results = search_yahoo_tickers(search_query)
            if results:
                options = {
                    f"{r['symbol']}  —  {r['name']}": r["symbol"]
                    for r in results
                }
                chosen_label = st.radio(
                    "Select a result",
                    list(options.keys()),
                    index=None,
                    key="search_results",
                )
                if chosen_label:
                    chosen_symbol = options[chosen_label]
                    is_added = chosen_symbol in all_tickers

                    if is_added:
                        btn_label = f"Remove {chosen_symbol}"
                        btn_type = "secondary"
                    else:
                        btn_label = f"Add {chosen_symbol}"
                        btn_type = "primary"

                    if st.button(
                        btn_label,
                        width="stretch",
                        type=btn_type,
                    ):
                        if is_added:
                            if chosen_symbol in st.session_state.custom_tickers:
                                st.session_state.custom_tickers.remove(
                                    chosen_symbol
                                )
                                save_custom_tickers(
                                    st.session_state.custom_tickers
                                )
                        else:
                            st.session_state.custom_tickers.append(
                                chosen_symbol
                            )
                            save_custom_tickers(
                                st.session_state.custom_tickers
                            )
                            # Auto-fetch and ingest news for the new ticker
                            with st.spinner(f"Fetching news for {chosen_symbol}…"):
                                from trader_agent.core.rss_fetcher import fetch_news_for_ticker
                                from trader_agent.core.ingestion import ingest_news
                                news_docs = fetch_news_for_ticker(chosen_symbol)
                                if news_docs:
                                    ingest_news(news_docs)
                        st.rerun()
            else:
                st.caption("No results found.")

    st.divider()

    # ── Action Budget (per-ticker) ───────────────────────────────────
    _sel_actions = st.session_state.actions_today.get(selected_ticker, 0)
    st.markdown(f"### Daily Budget — {selected_ticker}")
    budget_pct = (
        _sel_actions / MAX_ACTIONS_PER_DAY if MAX_ACTIONS_PER_DAY > 0 else 0
    )
    st.progress(min(budget_pct, 1.0))
    st.caption(f"{_sel_actions} / {MAX_ACTIONS_PER_DAY} actions used")

    st.divider()

    # ── Status Indicators ────────────────────────────────────────────
    st.markdown("### Status")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.checkbox("OpenAI", value=is_openai_valid(), disabled=True)
    with col_s2:
        st.checkbox("Discord", value=is_discord_valid(), disabled=True)

    st.divider()

    # ── Configuration ────────────────────────────────────────────────
    with st.expander("Configuration"):
        cost_per_cycle = estimate_cost_per_cycle(LLM_MODEL)
        cost_per_day = estimate_cost_per_day(LLM_MODEL)
        st.markdown(
            f"""
| Setting | Value |
|---------|-------|
| Model | `{LLM_MODEL}` |
| Interval | {RUN_INTERVAL_SECONDS}s |
| Chart Period | {CHART_PERIOD} |
| Chart Interval | {CHART_INTERVAL} |
| Cost per cycle | ~{cost_per_cycle:.2f}¢ |
| Cost per day | ~${cost_per_day/100:.2f} |
"""
        )


# ── Tabs ─────────────────────────────────────────────────────────────────────
t_stocks, t_dash, t_analysis, t_news, t_charts, t_pipe = st.tabs(
    [
        "Stocks",
        "Dashboard",
        "Analysis",
        "News Feed",
        "Charts",
        "Pipeline",
    ]
)

with t_stocks:
    tab_stocks.render(selected_ticker)

with t_dash:
    tab_dashboard.render(selected_ticker)

with t_analysis:
    tab_analysis.render(selected_ticker)

with t_news:
    tab_news.render(selected_ticker)

with t_charts:
    tab_charts.render(selected_ticker)

with t_pipe:
    tab_pipeline.render(selected_ticker)
