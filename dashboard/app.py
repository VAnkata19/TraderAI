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
    get_available_openai_models,
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
    with st.expander("Configuration", expanded=True):
        # Model selection with dynamic discovery
        available_models = get_available_openai_models()
        
        try:
            current_model_idx = available_models.index(LLM_MODEL)
        except ValueError:
            current_model_idx = 0  # Default to first available model
            
        selected_model = st.selectbox(
            "Model", 
            available_models, 
            index=current_model_idx,
            key="config_model"
        )
        
        # Interval (Run Interval)
        selected_interval = st.number_input(
            "Interval (seconds)",
            min_value=60,
            max_value=3600,
            value=RUN_INTERVAL_SECONDS,
            step=60,
            key="config_interval"
        )
        
        # Chart Period
        period_options = ["1d", "2d", "5d", "1mo", "3mo"]
        current_period_idx = period_options.index(CHART_PERIOD) if CHART_PERIOD in period_options else 1
        selected_period = st.selectbox(
            "Chart Period",
            period_options,
            index=current_period_idx,
            key="config_chart_period"
        )
        
        # Chart Interval
        interval_options = ["1m", "2m", "5m", "15m", "30m", "1h", "1d"]
        current_interval_idx = interval_options.index(CHART_INTERVAL) if CHART_INTERVAL in interval_options else 2
        selected_chart_interval = st.selectbox(
            "Chart Interval",
            interval_options,
            index=current_interval_idx,
            key="config_chart_interval"
        )
        
        # Timezone Selection
        timezone_options = [
            "US/Eastern",     # EST/EDT
            "US/Central",     # CST/CDT  
            "US/Mountain",    # MST/MDT
            "US/Pacific",     # PST/PDT
            "Europe/London",  # GMT/BST
            "Europe/Paris",   # CET/CEST
            "Europe/Berlin",  # CET/CEST
            "Asia/Tokyo",     # JST
            "Asia/Hong_Kong", # HKT
            "Asia/Shanghai",  # CST
            "Australia/Sydney", # AEST/AEDT
            "UTC"             # UTC
        ]
        
        # Initialize timezone setting if not set
        if "selected_timezone" not in st.session_state:
            import pytz
            from datetime import datetime
            # Auto-detect local timezone as default
            local_tz = datetime.now().astimezone().tzinfo 
            local_tz_name = str(local_tz)
            
            # Try to match with available options
            if local_tz_name in timezone_options:
                default_idx = timezone_options.index(local_tz_name)
            else:
                # Default to Eastern time (market timezone) if no match
                default_idx = 0
            st.session_state.selected_timezone = timezone_options[default_idx]
        
        current_tz_idx = timezone_options.index(st.session_state.selected_timezone) if st.session_state.selected_timezone in timezone_options else 0
        selected_timezone = st.selectbox(
            "Display Timezone",
            timezone_options,
            index=current_tz_idx,
            key="config_timezone",
            help="Timezone for chart display. Market data always uses Eastern time for market hours detection."
        )
        
        # Update session state when timezone changes
        if selected_timezone != st.session_state.selected_timezone:
            st.session_state.selected_timezone = selected_timezone
            st.rerun()
        
        st.divider()
        
        # Dynamic cost calculations - use the current widget values directly
        cost_per_cycle = estimate_cost_per_cycle(selected_model)
        cycles_per_day = (24 * 60 * 60) / selected_interval
        cost_per_day = cost_per_cycle * cycles_per_day
        
        # Display calculated costs
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Cost per cycle", 
                f"{cost_per_cycle:.3f}¢",
                help="Estimated cost per analysis cycle"
            )
        with col2:
            st.metric(
                "Cost per day", 
                f"${cost_per_day/100:.2f}",
                help="Estimated daily cost based on interval"
            )


# Set default selected_ticker if not set
if "selected_ticker" not in st.session_state or not st.session_state.selected_ticker:
    st.session_state.selected_ticker = all_tickers[0] if all_tickers else None

pg.run()
