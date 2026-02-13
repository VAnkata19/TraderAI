"""
Page: Stocks — real-time stock monitoring with looping analysis.
"""

import streamlit as st

from config import MAX_ACTIONS_PER_DAY
from dashboard.helpers import (
    get_all_tickers,
    get_ticker_data,
    get_ticker_info,
    is_analysis_running,
    start_analysis_loop,
    stop_analysis_loop,
    get_time_until_next_run,
    search_yahoo_tickers,
    save_custom_tickers,
    create_mini_price_chart,
    clear_data_cache,
)


def get_decision_badge_html(decision: str) -> str:
    """Generate HTML for a styled decision badge."""
    if decision == "buy":
        return '<span class="decision-badge decision-badge-buy"><span class="arrow"></span>BUY</span>'
    elif decision == "sell":
        return '<span class="decision-badge decision-badge-sell"><span class="arrow"></span>SELL</span>'
    else:
        return '<span class="decision-badge decision-badge-hold"><span class="arrow"></span>HOLD</span>'


def get_latest_decision_for_ticker(ticker: str) -> str | None:
    """Get the most recent decision for a ticker."""
    for decision in st.session_state.decisions:
        if decision.get("ticker") == ticker:
            return decision.get("decision")
    return None


@st.fragment(run_every=1)
def timer_fragment(ticker: str, running: bool) -> None:
    """Fragment that updates only the timer every 1 second."""
    if not running:
        return
    try:
        mins, secs = get_time_until_next_run(ticker)
        # Use a more isolated container to prevent content bleeding
        with st.container():
            st.markdown(f"**Next run:** {mins}m {secs}s")
    except Exception:
        # Fail silently if timer calculation fails to prevent app crashes
        pass


st.header("Stocks")

# ── Refresh Data Button ────────────────────────────────────────────  
col_refresh, _ = st.columns([1, 4])
with col_refresh:
    if st.button("🔄 Refresh Data", type="secondary", help="Clear cached data and fetch fresh market data"):
        clear_data_cache()
        st.success("Data cache cleared! Charts will show fresh data.", icon="✅")
        st.rerun()

all_tickers = get_all_tickers()

# ── Add Ticker (top-right popover) ────────────────────────────────────
_, col_add = st.columns([4, 1])
with col_add:
    with st.popover("Add Ticker", width="stretch"):
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
                                from core.rss_fetcher import fetch_news_for_ticker
                                from core.ingestion import ingest_news
                                news_docs = fetch_news_for_ticker(chosen_symbol)
                                if news_docs:
                                    ingest_news(news_docs)
                        st.rerun()
            else:
                st.caption("No results found.")

for ticker in all_tickers:
    running = is_analysis_running(ticker)

    with st.container(border=True):
        col_info, col_chart, col_price, col_right = st.columns([0.4, 1.5, 0.6, 1.0])

        with col_info:
            st.markdown(f"### {ticker}", help=None)
            actions_used = st.session_state.actions_today.get(ticker, 0)
            st.markdown(f"**Budget:** {actions_used}/{MAX_ACTIONS_PER_DAY}")

            latest = get_latest_decision_for_ticker(ticker)
            if latest:
                decision_html = get_decision_badge_html(latest)
                st.markdown(f"**Latest:** {decision_html}", unsafe_allow_html=True)
            else:
                st.markdown("**Latest:** —")

            # Show next run info below latest - updates every 1 second via fragment
            if running:
                timer_fragment(ticker, running)

        with col_chart:
            try:
                df = get_ticker_data(ticker, period="1d", interval="1m")
                if not df.empty:
                    # Use the helper function with market hours visualization and selected timezone
                    display_timezone = getattr(st.session_state, 'selected_timezone', 'US/Eastern')
                    fig = create_mini_price_chart(df, ticker, display_timezone)
                    if fig.data:  # Only show if chart has data
                        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
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

        with col_right:
            # Status + Start/Stop row
            r1, r2 = st.columns(2)
            with r1:
                if running:
                    st.success("🟢 Active")
                else:
                    st.error("⭕ Inactive")
            with r2:
                if running:
                    if st.button("⏹ Stop", key=f"stop_{ticker}", width='stretch', type="secondary"):
                        stop_analysis_loop(ticker)
                        st.rerun()
                else:
                    if st.button("▶ Start", key=f"start_{ticker}", width='stretch', type="primary"):
                        start_analysis_loop(ticker)
                        st.rerun()

            # Action buttons row — 3 equal columns
            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button("Analysis", key=f"analysis_{ticker}", type="secondary", width='stretch'):
                    st.session_state.selected_ticker = ticker
                    st.switch_page(st.session_state._page_analysis)
            with a2:
                if st.button("Charts", key=f"charts_{ticker}", type="secondary", width='stretch'):
                    st.session_state.selected_ticker = ticker
                    st.switch_page(st.session_state._page_charts)
            with a3:
                if st.button("News", key=f"news_{ticker}", type="secondary", width='stretch'):
                    st.session_state.selected_ticker = ticker
                    st.switch_page(st.session_state._page_news)