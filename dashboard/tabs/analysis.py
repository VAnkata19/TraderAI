"""
Page: Analysis — single-ticker on-demand analysis.
"""

import traceback
from datetime import datetime, timezone

import streamlit as st

from config import OPENAI_API_KEY
from dashboard.helpers import save_actions_today, save_decisions
from typing import cast
from graph.graph import GraphState

def _deduplicate_documents(documents):
    """Remove duplicate documents by page_content."""
    seen = set()
    deduped = []
    for doc in documents:
        content_hash = hash(doc.page_content)
        if content_hash not in seen:
            seen.add(content_hash)
            deduped.append(doc)
    return deduped


selected_ticker = st.session_state.selected_ticker

st.markdown("## Single-Ticker Analysis")
st.header(f"{selected_ticker}")

# ── Check for historical decision view ───────────────────────────────────────
if "historical_decision" in st.session_state and st.session_state.historical_decision:
    hist = st.session_state.historical_decision
    
    # Display banner indicating this is historical data
    st.info("📋 Viewing historical analysis.")
    
    # Parse timestamp
    ts = hist.get("timestamp", "")
    if isinstance(ts, datetime):
        time_display = ts.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        try:
            time_display = str(ts)[:19]
        except Exception:
            time_display = "Unknown"
    
    st.caption(f"Analysis performed at: {time_display}")
    st.divider()
    
    # Display decision and metrics
    decision = hist.get("decision", "HOLD").upper()
    
    # Set color based on decision
    if decision == "BUY":
        decision_color = "#00ff00"  # Green
    elif decision == "SELL":
        decision_color = "#ff4444"  # Red
    else:  # HOLD
        decision_color = "#ffaa00"  # Orange

    m1, m2, m3 = st.columns(3)
    with m1:
        # Create metric-like display with colored decision
        st.markdown(f"""
        <div style="padding: 0.5rem 0; display: flex; flex-direction: column; gap: 0.25rem;">
            <div style="font-size: 0.875rem; font-weight: 400; color: rgba(250, 250, 250, 0.6);">Decision</div>
            <div style="font-size: 2.25rem; font-weight: 600; color: {decision_color}; line-height: 1.2;">{decision}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.metric("Executed", "Yes ✓" if hist.get("executed") else "No")
    with m3:
        actions_at_time = hist.get("actions_today", 0)
        st.metric("Actions at time", str(actions_at_time))

    with st.expander("📝 Reasoning", expanded=True):
        st.write(hist.get("reasoning", "N/A"))

    with st.expander("News Summary"):
        st.write(hist.get("news_summary", "N/A"))

    with st.expander("Chart Summary"):
        st.write(hist.get("chart_summary", "N/A"))

    if hist.get("portfolio_context"):
        with st.expander("Portfolio Context"):
            st.write(hist.get("portfolio_context", "N/A"))

    if hist.get("order_result"):
        with st.expander("Order Result"):
            st.write(hist.get("order_result", "N/A"))
    
    st.divider()
    
    st.stop()

# ── Normal analysis flow ─────────────────────────────────────────────────────

if not OPENAI_API_KEY:
    st.error(
        "⚠️ OpenAI API key not configured. "
        "Set `OPENAI_API_KEY` in your `.env` file."
    )
    st.stop()

col_left, col_right = st.columns([3, 1])

with col_right:
    st.markdown("### Controls")
    run_btn = st.button(
        "Run Analysis",
        type="primary",
        width="stretch",
        key="run_single",
    )
    _ticker_actions = st.session_state.actions_today.get(
        selected_ticker, 0
    )
    st.caption(
        f"Budget: {_ticker_actions} / {st.session_state.get('max_actions_per_day', 5)} for {selected_ticker}"
    )

if run_btn:
    with col_left:
        with st.status(
            "Running analysis pipeline…", expanded=True
        ) as status:
            try:
                # ── 1. Fetch and deduplicate news ────────────────────
                st.write("Fetching news…")
                from core.rss_fetcher import fetch_news_for_ticker

                try:
                    news_docs = fetch_news_for_ticker(selected_ticker)
                    st.write(f"   ↳ Fetched {len(news_docs)} articles")

                    news_docs = _deduplicate_documents(news_docs)
                    st.write(f"   ↳ After dedup: {len(news_docs)} unique articles")
                except Exception as e:
                    st.warning(f"⚠️ News fetch warning: {e}")
                    news_docs = []

                # ── 2. Fetch and deduplicate chart data ──────────────
                st.write("Fetching chart data…")
                from core.chart_fetcher import (
                    fetch_chart_for_ticker,
                )

                try:
                    chart_docs = fetch_chart_for_ticker(selected_ticker)
                    st.write(f"   ↳ Fetched {len(chart_docs)} candles")

                    chart_docs = _deduplicate_documents(chart_docs)
                    st.write(f"   ↳ After dedup: {len(chart_docs)} unique candles")
                except Exception as e:
                    st.warning(f"⚠️ Chart fetch warning: {e}")
                    chart_docs = []

                # ── 3. Ingest into vector stores ─────────────────────
                st.write("💾 Ingesting into vector stores…")
                from core.ingestion import (
                    ingest_chart,
                    ingest_news,
                )

                try:
                    ingest_news(news_docs)
                    st.write("   ✓ News ingested")
                except Exception as e:
                    st.warning(f"⚠️ News ingest warning: {e}")

                try:
                    ingest_chart(chart_docs)
                    st.write("   ✓ Chart ingested")
                except Exception as e:
                    st.warning(f"⚠️ Chart ingest warning: {e}")

                # ── 4. Run LangGraph pipeline ────────────────────────
                st.write("Running LangGraph pipeline…")
                from graph.graph import app as graph_app

                _current_actions = st.session_state.actions_today.get(
                    selected_ticker, 0
                )

                try:
                    result = graph_app.invoke( 
                        cast(GraphState, {
                            "ticker": selected_ticker,
                            "news_documents": [],
                            "chart_documents": [],
                            "news_summary": "",
                            "chart_summary": "",
                            "portfolio_context": "",
                            "decision": "",
                            "reasoning": "",
                            "actions_today": _current_actions,
                            "max_actions": st.session_state.get('max_actions_per_day', 5),
                            "executed": False,
                            "order_result": "",
                        })
                    )
                    st.write("   ✓ Pipeline complete")
                except Exception as e:
                    st.error(f"❌ Pipeline failed: {e}")
                    st.error(traceback.format_exc())
                    status.update(label="Pipeline failed", state="error")
                    st.stop()

                status.update(
                    label="Analysis complete!", state="complete"
                )

            except Exception as e:
                status.update(
                    label=f"Analysis failed: {e}", state="error"
                )
                st.error(f"❌ Unexpected error: {e}")
                st.error(traceback.format_exc())
                st.stop()

        # ── Display results ──────────────────────────────────────
        st.divider()

        decision = result["decision"]
        
        # Set color based on decision
        if decision.upper() == "BUY":
            decision_color = "#00ff00"  # Green
        elif decision.upper() == "SELL":
            decision_color = "#ff4444"  # Red
        else:  # HOLD
            decision_color = "#ffaa00"  # Orange

        m1, m2, m3 = st.columns(3)
        with m1:
            # Create metric-like display with colored decision
            st.markdown(f"""
            <div style="padding: 0.5rem 0; display: flex; flex-direction: column; gap: 0.25rem;">
                <div style="font-size: 0.875rem; font-weight: 400; color: rgba(250, 250, 250, 0.6);">Decision</div>
                <div style="font-size: 2.25rem; font-weight: 600; color: {decision_color}; line-height: 1.2;">{decision.upper()}</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.metric(
                "Executed", "Yes ✓" if result["executed"] else "No"
            )
        with m3:
            st.metric(
                "Actions Today",
                f"{result['actions_today']} / {st.session_state.get('max_actions_per_day', 5)}",
            )

        with st.expander("📝 Reasoning", expanded=True):
            st.write(result["reasoning"])

        with st.expander("News Summary"):
            st.write(result.get("news_summary", "N/A"))

        with st.expander("Chart Summary"):
            st.write(result.get("chart_summary", "N/A"))

        # ── Update session state ─────────────────────────────────
        if result.get("executed"):
            st.session_state.actions_today[selected_ticker] = result[
                "actions_today"
            ]
            save_actions_today(st.session_state.actions_today)

        st.session_state.decisions.insert(
            0,
            {
                "timestamp": datetime.now(timezone.utc),
                "ticker": selected_ticker,
                "decision": decision,
                "reasoning": result["reasoning"],
                "news_summary": result.get("news_summary", ""),
                "chart_summary": result.get("chart_summary", ""),
                "portfolio_context": result.get("portfolio_context", ""),
                "executed": result["executed"],
                "order_result": result.get("order_result", ""),
                "actions_today": result.get("actions_today", 0),
            },
        )
        save_decisions(st.session_state.decisions)
