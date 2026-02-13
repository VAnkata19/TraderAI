"""
Page: Stocks — real-time stock monitoring with looping analysis.
"""

import streamlit as st

from dashboard.helpers import (
    get_all_tickers,
    get_ticker_data,
    get_ticker_info,
    is_analysis_running,
    start_analysis_loop,
    stop_analysis_loop,
    get_time_until_next_run,
    search_yahoo_tickers,
    save_tickers,
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

all_tickers = get_all_tickers()

# ── Add Ticker & Control All ──────────────────────────────────────────
_, col_add, col_control_all = st.columns([3, 1, 1])

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
                            # Remove ticker
                            if chosen_symbol in st.session_state.tickers:
                                st.session_state.tickers.remove(
                                    chosen_symbol
                                )
                                save_tickers(
                                    st.session_state.tickers
                                )
                        else:
                            # Add ticker
                            st.session_state.tickers.append(
                                chosen_symbol
                            )
                            save_tickers(
                                st.session_state.tickers
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

with col_control_all:
    # Check how many tickers are currently running
    running_tickers = [ticker for ticker in all_tickers if is_analysis_running(ticker)]
    all_running = len(running_tickers) == len(all_tickers) and len(all_tickers) > 0
    some_running = len(running_tickers) > 0
    
    if all_running:
        # All tickers are running - show Stop All button
        if st.button("⏹ Stop All", width="stretch", type="secondary"):
            for ticker in all_tickers:
                if is_analysis_running(ticker):
                    stop_analysis_loop(ticker)
            st.rerun()
    elif some_running:
        # Some tickers are running - show Stop All button (for consistency)  
        if st.button("⏹ Stop All", width="stretch", type="secondary"):
            for ticker in all_tickers:
                if is_analysis_running(ticker):
                    stop_analysis_loop(ticker)
            st.rerun()
    else:
        # No tickers running - show Start All button
        if st.button("▶ Start All", width="stretch", type="primary"):
            for ticker in all_tickers:
                if not is_analysis_running(ticker):
                    start_analysis_loop(ticker)
            st.rerun()

# ── Individual Ticker Controls ──────────────────────────────────────────────
for ticker in all_tickers:
    running = is_analysis_running(ticker)

    with st.container(border=True):
        col_info, col_chart, col_price, col_right = st.columns([0.4, 1.5, 0.6, 1.0])

        with col_info:
            st.markdown(f"### {ticker}", help=None)
            actions_used = st.session_state.actions_today.get(ticker, 0)
            max_actions = st.session_state.get('max_actions_per_day', 5)
            max_actions_display = "∞" if max_actions == -1 else str(max_actions)
            st.markdown(f"**Budget:** {actions_used}/{max_actions_display}")

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