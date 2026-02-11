"""
Tab: Charts — interactive candlestick / line charts.
"""

import plotly.graph_objects as go
import streamlit as st

from dashboard.helpers import (
    create_candlestick_chart,
    get_ticker_data,
)


def render(selected_ticker: str) -> None:
    st.header(f"Chart — {selected_ticker}")

    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        period = st.selectbox(
            "Period",
            ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
            index=0,
        )
    with cc2:
        interval_map = {
            "1d": ["1m", "5m", "15m", "30m", "1h"],
            "5d": ["5m", "15m", "30m", "1h"],
            "1mo": ["30m", "1h", "1d"],
            "3mo": ["1h", "1d", "1wk"],
            "6mo": ["1d", "1wk"],
            "1y": ["1d", "1wk", "1mo"],
        }
        avail = interval_map.get(period, ["1d"])
        interval = st.selectbox("Interval", avail, index=1 if period == "1d" else 0)
    with cc3:
        chart_type = st.selectbox("Chart Type", ["Candlestick", "Line"])

    try:
        df = get_ticker_data(
            selected_ticker, period=period, interval=interval
        )
        if not df.empty:
            if chart_type == "Candlestick":
                fig = create_candlestick_chart(df, selected_ticker)
            else:
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df["Close"],
                        mode="lines",
                        name="Close",
                        line=dict(color="#3498db", width=2),
                    )
                )
                fig.update_layout(
                    template="plotly_dark",
                    height=500,
                    margin=dict(l=0, r=0, t=10, b=0),
                )
            st.plotly_chart(fig, width="stretch")

            # ── Stats row ────────────────────────────────────────────
            s1, s2, s3, s4, s5 = st.columns(5)
            with s1:
                st.metric("Open", f"${df['Open'].iloc[-1]:.2f}")
            with s2:
                st.metric("Period High", f"${df['High'].max():.2f}")
            with s3:
                st.metric("Period Low", f"${df['Low'].min():.2f}")
            with s4:
                st.metric("Close", f"${df['Close'].iloc[-1]:.2f}")
            with s5:
                st.metric("Avg Volume", f"{int(df['Volume'].mean()):,}")
        else:
            st.warning("No data available for this selection.")
    except Exception as e:
        st.error(f"Failed to fetch chart data: {e}")
