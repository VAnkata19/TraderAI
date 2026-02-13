"""
TraderAI — Streamlit Dashboard
===============================
Multi-page app coordinator: sidebar, CSS, session state, and navigation.

Run with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Ensure the package root is importable when launched with `streamlit run`
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from config import (
    TICKERS,
    MAX_ACTIONS_PER_DAY,
    RUN_INTERVAL_SECONDS,
    LLM_MODEL,
    DISCORD_WEBHOOK_URL,
    OPENAI_API_KEY,
    CHART_PERIOD,
    CHART_INTERVAL,
)
from dashboard.helpers import (
    init_session_state,
    get_all_tickers,
    search_yahoo_tickers,
    save_custom_tickers,
    is_openai_valid,
    is_discord_valid,
    estimate_cost_per_cycle,
    estimate_cost_per_day,
)


# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TraderAI Dashboard",
    page_icon="�",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
def load_css():
    """Load external CSS file"""
    css_file = Path(__file__).parent / "style.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("CSS file not found: style.css")

load_css()

# ── Session State ────────────────────────────────────────────────────────────
init_session_state()

all_tickers = get_all_tickers()

# ── Navigation ───────────────────────────────────────────────────────────────
_TABS_DIR = Path(__file__).resolve().parent / "tabs"

_analysis_page = st.Page(str(_TABS_DIR / "analysis.py"), title="Analysis", url_path="analysis")
_news_page = st.Page(str(_TABS_DIR / "news.py"), title="News Feed", url_path="news")
_charts_page = st.Page(str(_TABS_DIR / "charts.py"), title="Charts", url_path="charts")

# Store page refs for switch_page (these pages are hidden from sidebar nav)
st.session_state._page_analysis = _analysis_page
st.session_state._page_news = _news_page
st.session_state._page_charts = _charts_page

pages = [
    st.Page(str(_TABS_DIR / "dashboard.py"), title="Dashboard", url_path="dashboard", default=True),
    st.Page(str(_TABS_DIR / "stocks.py"), title="Stocks", url_path="stocks"),
    st.Page(str(_TABS_DIR / "transactions.py"), title="Transactions", url_path="transactions"),
    st.Page(str(_TABS_DIR / "pipeline.py"), title="Pipeline", url_path="pipeline"),
    _analysis_page,
    _news_page,
    _charts_page,
]

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# TraderAI")
    st.caption("LLM-powered trading agent")
    st.divider()

pg = st.navigation(pages)

with st.sidebar:

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


# Set default selected_ticker if not set
if "selected_ticker" not in st.session_state or not st.session_state.selected_ticker:
    st.session_state.selected_ticker = all_tickers[0] if all_tickers else None

pg.run()
