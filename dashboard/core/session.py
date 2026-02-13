"""
Session state management and initialization for the dashboard.
"""

import streamlit as st
from datetime import datetime, timezone
from dashboard.utils.storage import load_actions_today, load_decisions, load_tickers, save_actions_today
from config import MAX_ACTIONS_PER_DAY


def init_session_state() -> None:
    """Initialize dashboard session state variables."""
    # ── Trading loop management ─────────────────────────────────────────
    if "analysis_threads" not in st.session_state:
        st.session_state.analysis_threads = {}
    
    if "stop_flags" not in st.session_state:
        st.session_state.stop_flags = {}
    
    # ── Decision history ────────────────────────────────────────────────
    if "decisions" not in st.session_state:
        st.session_state.decisions = load_decisions()
    
    # ── Today's action tracking ─────────────────────────────────────────
    if "actions_today" not in st.session_state or not isinstance(
        st.session_state.actions_today, dict
    ):
        st.session_state.actions_today = load_actions_today()
    
    # ── Current day tracking for auto-reset ────────────────────────────
    if "current_day" not in st.session_state:
        st.session_state.current_day = datetime.now(timezone.utc).date()
    
    # ── Tickers management ──────────────────────────────────────────────
    if "tickers" not in st.session_state:
        st.session_state.tickers = load_tickers()
    
    # ── Selected ticker for detail pages ───────────────────────────────
    if "selected_ticker" not in st.session_state:
        st.session_state.selected_ticker = None
    
    # ── Configuration state ─────────────────────────────────────────────
    if "config_initialized" not in st.session_state:
        st.session_state.config_initialized = True
    
    # ── Max actions per day setting ─────────────────────────────────────
    if "max_actions_per_day" not in st.session_state:
        st.session_state.max_actions_per_day = MAX_ACTIONS_PER_DAY

    # ── Reset counters at midnight UTC ──────────────────────────────────
    now = datetime.now(timezone.utc)
    if now.date() != st.session_state.current_day:
        st.session_state.actions_today = load_actions_today()
        st.session_state.current_day = now.date()
        save_actions_today(st.session_state.actions_today)


def get_analysis_thread_status(ticker: str) -> bool:
    """Check if analysis thread is running for a ticker."""
    thread = st.session_state.analysis_threads.get(ticker)
    return thread is not None and thread.is_alive()


def set_selected_ticker(ticker: str) -> None:
    """Set the selected ticker for detail pages."""
    st.session_state.selected_ticker = ticker


def get_selected_ticker() -> str | None:
    """Get the currently selected ticker."""
    return st.session_state.get("selected_ticker")