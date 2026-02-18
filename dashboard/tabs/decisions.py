"""
Decisions History — Full log of all LLM trading decisions with details.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

st.header("Decision History")

decisions = st.session_state.get("decisions", [])

if not decisions:
    st.info("No decisions recorded yet. Run an analysis to see decisions here.")
    st.stop()

# ── Filters ──────────────────────────────────────────────────────────────────
col_filter1, col_filter2, col_filter3 = st.columns(3)

all_tickers = sorted(set(d.get("ticker", "?") for d in decisions))
all_actions = sorted(set(d.get("decision", "").upper() for d in decisions))

with col_filter1:
    filter_ticker = st.selectbox(
        "Filter by Ticker",
        options=["All"] + all_tickers,
    )

with col_filter2:
    filter_action = st.selectbox(
        "Filter by Decision",
        options=["All"] + all_actions,
    )

with col_filter3:
    filter_executed = st.selectbox(
        "Filter by Execution",
        options=["All", "Executed", "Not Executed"],
    )

# Apply filters
filtered = decisions
if filter_ticker != "All":
    filtered = [d for d in filtered if d.get("ticker") == filter_ticker]
if filter_action != "All":
    filtered = [d for d in filtered if d.get("decision", "").upper() == filter_action]
if filter_executed == "Executed":
    filtered = [d for d in filtered if d.get("executed")]
elif filter_executed == "Not Executed":
    filtered = [d for d in filtered if not d.get("executed")]

st.caption(f"Showing {len(filtered)} of {len(decisions)} decisions")
st.divider()

# ── Decision Cards ───────────────────────────────────────────────────────────
DECISION_COLORS = {
    "BUY": "#00ff00",
    "SELL": "#ff4444",
    "HOLD": "#ffaa00",
}

for i, d in enumerate(filtered):
    dec = d.get("decision", "hold").upper()
    ticker = d.get("ticker", "?")
    color = DECISION_COLORS.get(dec, "#888888")
    executed = d.get("executed", False)
    
    # Parse timestamp
    ts = d.get("timestamp", "")
    if isinstance(ts, datetime):
        time_display = ts.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        try:
            time_display = str(ts)[:19]
        except Exception:
            time_display = "Unknown"

    # Single row with all info and button
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.5rem 0;
        ">
            <span style="
                font-size: 1.2rem;
                font-weight: 700;
                color: white;
            ">{ticker}</span>
            <span style="
                font-size: 0.95rem;
                font-weight: 600;
                color: {color};
                background: {color}22;
                padding: 0.15rem 0.7rem;
                border-radius: 4px;
                border: 1px solid {color}44;
            ">{dec}</span>
            <span style="
                font-size: 0.85rem;
                color: {'#00ff00' if executed else '#888888'};
            ">{'✓ Executed' if executed else '✕ Not Executed'}</span>
            <span style="
                font-size: 0.8rem;
                color: rgba(250,250,250,0.5);
                margin-left: auto;
            ">{time_display}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # View Analysis button
        if st.button("View Analysis", key=f"view_{i}", use_container_width=True):
            # Store the historical decision in session state
            st.session_state["historical_decision"] = d
            st.session_state.selected_ticker = ticker
            st.switch_page(st.session_state._page_analysis)

    st.divider()

