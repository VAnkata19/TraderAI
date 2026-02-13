"""
Page: Dashboard — full trading command center.
"""

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import LLM_MODEL, RUN_INTERVAL_SECONDS
from dashboard.helpers import (
    get_all_tickers,
    get_ticker_info,
    is_analysis_running,
    estimate_cost_per_cycle,
)


# ── Decision Badge Helper ───────────────────────────────────────────────────
def get_decision_badge_html(decision: str) -> str:
    """Generate HTML for a styled decision badge."""
    if decision == "buy":
        return '<span class="decision-badge decision-badge-buy"><span class="arrow"></span>BUY</span>'
    elif decision == "sell":
        return '<span class="decision-badge decision-badge-sell"><span class="arrow"></span>SELL</span>'
    else:
        return '<span class="decision-badge decision-badge-hold"><span class="arrow"></span>HOLD</span>'


# ── Alpaca data fetchers (cached) ───────────────────────────────────────────
@st.cache_data(ttl=30)
def _fetch_account():
    try:
        from core.alpaca import get_account
        return get_account()
    except Exception:
        return None


@st.cache_data(ttl=30)
def _fetch_positions():
    try:
        from core.alpaca import get_positions
        return get_positions()
    except Exception:
        return []


@st.cache_data(ttl=60)
def _fetch_recent_orders():
    try:
        from core.alpaca import get_orders
        return get_orders(status="closed", limit=20)
    except Exception:
        return []


# ── Header ───────────────────────────────────────────────────────────────────
st.header("Dashboard")

all_tickers = get_all_tickers()
account = _fetch_account()
positions = _fetch_positions()

# ── Row 1: Account KPIs ─────────────────────────────────────────────────────
if account:
    equity = float(account.get("equity", 0))
    buying_power = float(account.get("buying_power", 0))
    cash = float(account.get("cash", 0))
    last_equity = float(account.get("last_equity", equity))
    daily_pl = equity - last_equity
    daily_pl_pct = (daily_pl / last_equity * 100) if last_equity else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Portfolio Value", f"${equity:,.2f}", f"{daily_pl_pct:+.2f}%")
    with k2:
        st.metric("Daily P/L", f"${daily_pl:,.2f}")
    with k3:
        st.metric("Buying Power", f"${buying_power:,.2f}")
    with k4:
        st.metric("Cash", f"${cash:,.2f}")
else:
    st.warning("Could not connect to Alpaca — account data unavailable.")

st.divider()

# ── Row 2: Positions & Allocation ────────────────────────────────────────────
col_positions, col_chart = st.columns([3, 2])

with col_positions:
    st.subheader("Open Positions")
    if positions:
        rows = []
        for p in positions:
            qty = float(p["qty"])
            avg = float(p["avg_entry_price"])
            mv = float(p["market_value"])
            upl = float(p["unrealized_pl"])
            upl_pct = float(p["unrealized_plpc"]) * 100
            cur_price = float(p["current_price"])
            rows.append({
                "Symbol": p["symbol"],
                "Qty": int(qty),
                "Avg Entry": f"${avg:,.2f}",
                "Price": f"${cur_price:,.2f}",
                "Mkt Value": f"${mv:,.2f}",
                "P/L": f"${upl:,.2f}",
                "P/L %": f"{upl_pct:+.2f}%",
            })

        df_pos = pd.DataFrame(rows)
        st.dataframe(
            df_pos,
            width="stretch",
            hide_index=True,
            column_config={
                "P/L %": st.column_config.TextColumn("P/L %"),
            },
        )

        # Totals
        total_value = sum(float(p["market_value"]) for p in positions)
        total_pl = sum(float(p["unrealized_pl"]) for p in positions)
        tc1, tc2 = st.columns(2)
        with tc1:
            st.metric("Total Holdings", f"${total_value:,.2f}")
        with tc2:
            st.metric("Unrealised P/L", f"${total_pl:,.2f}")
    else:
        st.info("No open positions.")

with col_chart:
    st.subheader("Allocation")
    if positions:
        labels = [p["symbol"] for p in positions]
        values = [abs(float(p["market_value"])) for p in positions]

        # Add cash slice
        if account:
            cash_val = float(account.get("cash", 0))
            if cash_val > 0:
                labels.append("Cash")
                values.append(cash_val)

        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            textinfo="label+percent",
            marker=dict(colors=[
                "#3498db", "#2ecc71", "#e74c3c", "#f39c12",
                "#9b59b6", "#1abc9c", "#e67e22", "#95a5a6",
            ]),
        )])
        fig_pie.update_layout(
            template="plotly_dark",
            height=320,
            margin=dict(l=20, r=20, t=10, b=10),
            showlegend=False,
        )
        st.plotly_chart(fig_pie, width="stretch")
    else:
        # Show 100% cash
        if account:
            fig_pie = go.Figure(data=[go.Pie(
                labels=["Cash"],
                values=[float(account.get("cash", 0))],
                hole=0.45,
                marker=dict(colors=["#95a5a6"]),
            )])
            fig_pie.update_layout(
                template="plotly_dark",
                height=320,
                margin=dict(l=20, r=20, t=10, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig_pie, width="stretch")

st.divider()

# ── Row 3: Market Movers & Agent Activity ────────────────────────────────────
col_market, col_activity = st.columns([3, 2])

with col_market:
    st.subheader("Tracked Tickers")
    # Build a compact ticker table with sparkline-style info
    ticker_rows = []
    for t in all_tickers:
        info = get_ticker_info(t)
        running = is_analysis_running(t)
        if info:
            ticker_rows.append({
                "Ticker": t,
                "Price": info["price"],
                "Change %": info["change_pct"],
                "Agent": "🟢" if running else "⭕",
            })
        else:
            ticker_rows.append({
                "Ticker": t,
                "Price": None,
                "Change %": None,
                "Agent": "🟢" if running else "⭕",
            })

    if ticker_rows:
        df_tickers = pd.DataFrame(ticker_rows)
        st.dataframe(
            df_tickers,
            width="stretch",
            hide_index=True,
            column_config={
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Change %": st.column_config.NumberColumn("Change %", format="%.2f%%"),
                "Agent": st.column_config.TextColumn("Agent", width="small"),
            },
        )

with col_activity:
    st.subheader("Recent Decisions")
    decisions = st.session_state.get("decisions", [])
    if decisions:
        # Prepare data for table
        table_data = []
        for d in decisions[:8]:
            try:
                ts = d.get("timestamp", "")
                if hasattr(ts, "strftime"):
                    time_str = ts.strftime("%Y-%m-%d %H:%M")
                else:
                    time_str = str(ts)[:16] if ts else "Unknown"

                dec = d.get("decision", "hold").upper()
                ticker = d.get("ticker", "?")

                # Sanitize ticker and decision
                ticker = str(ticker)[:10]
                if dec not in ["BUY", "SELL", "HOLD"]:
                    dec = "HOLD"

                table_data.append({
                    "Ticker": ticker,
                    "Decision": dec,  # Just plain text for now
                    "Time": time_str
                })
            except Exception:
                continue
        
        if table_data:
            df_decisions = pd.DataFrame(table_data)
            
            # Apply color styling to the dataframe
            def color_decisions(val):
                if val == "BUY":
                    return "color: #00ff00"  # Green
                elif val == "SELL":
                    return "color: #ff4444"  # Red
                elif val == "HOLD":
                    return "color: #ffaa00"  # Orange
                return ""
            
            styled_df = df_decisions.style.applymap(color_decisions, subset=['Decision'])
            
            st.dataframe(
                styled_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "Decision": st.column_config.TextColumn("Decision", width="medium"),
                    "Time": st.column_config.TextColumn("Time", width="medium")
                }
            )
    else:
        st.caption("No decisions yet.")

st.divider()

# ── Row 4: System Stats ─────────────────────────────────────────────────────
st.subheader("System")
s1, s2, s3, s4 = st.columns(4)
with s1:
    active_loops = sum(1 for t in all_tickers if is_analysis_running(t))
    st.metric("Active Agents", f"{active_loops} / {len(all_tickers)}")
with s2:
    total_decisions = len(st.session_state.get("decisions", []))
    st.metric("Total Decisions", total_decisions)
with s3:
    total_actions = sum(st.session_state.get("actions_today", {}).values())
    st.metric("Actions Today", total_actions)
with s4:
    cost = estimate_cost_per_cycle(LLM_MODEL)
    st.metric("Cost / Cycle", f"{cost:.2f}¢")
