"""
Tab: Dashboard — market overview and recent decisions.
"""

import pandas as pd
import streamlit as st

from dashboard.helpers import get_all_tickers, get_ticker_info


def render(selected_ticker: str) -> None:
    st.header("Market Overview")

    all_tickers = get_all_tickers()

    # ── Price cards ──────────────────────────────────────────────────────
    cols = st.columns(min(len(all_tickers), 6))
    for i, t in enumerate(all_tickers):
        with cols[i % len(cols)]:
            info = get_ticker_info(t)
            if info:
                st.metric(
                    label=t,
                    value=f"${info['price']:.2f}",
                    delta=f"{info['change_pct']:+.2f}%",
                )
            else:
                st.metric(label=t, value="N/A")

    st.divider()

    # ── Recent Decisions ─────────────────────────────────────────────────
    st.subheader("📜 Recent Decisions")
    if st.session_state.decisions:
        df_dec = pd.DataFrame(st.session_state.decisions)
        st.dataframe(
            df_dec,
            width="stretch",
            column_config={
                "timestamp": st.column_config.DatetimeColumn(
                    "Time", format="YYYY-MM-DD HH:mm"
                ),
                "ticker": "Ticker",
                "decision": "Decision",
                "confidence": st.column_config.ProgressColumn(
                    "Confidence", min_value=0, max_value=1, format="%.2f"
                ),
                "executed": st.column_config.CheckboxColumn("Executed"),
                "reasoning": st.column_config.TextColumn(
                    "Reasoning", width="large"
                ),
            },
            hide_index=True,
        )
    else:
        st.info(
            "No decisions yet. Head to the **Stocks** tab to start a loop."
        )
