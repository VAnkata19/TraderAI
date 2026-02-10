"""
Tab: Stocks — real-time stock monitoring with looping analysis.
"""

import streamlit as st
import plotly.graph_objects as go

from trader_agent.config import MAX_ACTIONS_PER_DAY
from trader_agent.dashboard.helpers import (
    get_all_tickers,
    get_ticker_data,
    get_ticker_info,
    is_analysis_loop_running,
    start_analysis_loop,
    stop_analysis_loop,
    get_time_until_next_run,
)


def get_latest_decision_for_ticker(ticker: str) -> str | None:
    """Get the most recent decision for a ticker."""
    for decision in st.session_state.decisions:
        if decision.get("ticker") == ticker:
            return decision.get("decision")
    return None


@st.fragment(run_every=1)
def timer_fragment(ticker: str, running: bool) -> None:
    """Fragment that updates only the timer every 1 second."""
    if running:
        mins, secs = get_time_until_next_run(ticker)
        st.markdown(f"**Next run:** {mins}m {secs}s")


def render(selected_ticker: str) -> None:
    st.header("Stocks")
    st.caption("Monitor stocks with looping analysis every 5 minutes")

    all_tickers = get_all_tickers()

    for ticker in all_tickers:
        running = is_analysis_loop_running(ticker)

        with st.container(border=True):
            col_info, col_chart, col_price, col_control = st.columns([0.5, 1, 0.5, 0.8])

            with col_info:
                st.markdown(f"### {ticker}", help=None)
                actions_used = st.session_state.actions_today.get(ticker, 0)
                st.markdown(f"**Budget:** {actions_used}/{MAX_ACTIONS_PER_DAY}")
                
                latest = get_latest_decision_for_ticker(ticker)
                if latest:
                    decision_text = (
                        "🟢 BUY"
                        if latest == "buy"
                        else "🔴 SELL"
                        if latest == "sell"
                        else "🟡 HOLD"
                    )
                    st.markdown(f"**Latest:** {decision_text}")
                else:
                    st.markdown("**Latest:** —")
                
                # Show next run info below latest - updates every 1 second via fragment
                if running:
                    timer_fragment(ticker, running)

            with col_chart:
                try:
                    df = get_ticker_data(ticker, period="1d", interval="1m")
                    if not df.empty:
                        fig = go.Figure(data=[go.Candlestick(
                            x=df.index,
                            open=df["Open"],
                            high=df["High"],
                            low=df["Low"],
                            close=df["Close"],
                            increasing_line_color="#2ecc71",
                            decreasing_line_color="#e74c3c",
                        )])
                        fig.update_layout(
                            template="plotly_dark",
                            height=140,
                            margin=dict(l=0, r=0, t=0, b=0),
                            showlegend=False,
                            xaxis_rangeslider_visible=False,
                            xaxis=dict(showticklabels=False),
                        )
                        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
                except Exception:
                    pass
            
            with col_price:
                info = get_ticker_info(ticker)
                if info:
                    st.metric(
                        label="Price",
                        value=f"${info['price']:.2f}",
                        delta=f"{info['change_pct']:+.2f}%",
                    )

            with col_control:
                if running:
                    st.success("🟢 Active")
                    if st.button(
                        "⏹️  Stop",
                        key=f"stop_{ticker}",
                        width="stretch",
                        type="secondary",
                    ):
                        stop_analysis_loop(ticker)
                        st.rerun()
                else:
                    st.error("⭕ Inactive")
                    if st.button(
                        "▶️  Start",
                        key=f"start_{ticker}",
                        width="stretch",
                        type="primary",
                    ):
                        start_analysis_loop(ticker)
                        st.rerun()
