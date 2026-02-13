"""
Tab: Transactions — monitor Alpaca orders and fill activity.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY


def _parse_timestamp(ts: str | None) -> str:
    """Parse an ISO timestamp string into a readable format."""
    if not ts:
        return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


@st.cache_data(ttl=30)
def _fetch_orders(status: str, limit: int, symbols: str | None):
    from core.alpaca import get_orders

    return get_orders(status=status, limit=limit, symbols=symbols)


@st.cache_data(ttl=30)
def _fetch_fills(limit: int):
    from core.alpaca import get_fill_activity

    return get_fill_activity(limit=limit)


selected_ticker = st.session_state.selected_ticker
st.header("Transactions")
st.caption("Monitor Alpaca orders and fill activity")

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    st.warning(
        "Alpaca API credentials not configured. "
        "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env."
    )

# ── Filters ───────────────────────────────────────────────────────
col_status, col_ticker, col_limit, col_refresh = st.columns([1, 1, 0.7, 0.5])

with col_status:
    status_filter = st.selectbox(
        "Order Status",
        ["all", "open", "closed"],
        index=0,
        key="txn_status_filter",
    )

with col_ticker:
    ticker_filter = st.selectbox(
        "Filter by Ticker",
        ["All Tickers", selected_ticker],
        index=0,
        key="txn_ticker_filter",
    )

with col_limit:
    result_limit = st.selectbox(
        "Limit",
        [25, 50, 100],
        index=2,
        key="txn_limit",
    )

with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Refresh", key="txn_refresh", type="primary"):
        st.cache_data.clear()
        st.rerun()

symbols_param = ticker_filter if ticker_filter != "All Tickers" else None

st.divider()

# ── Orders ────────────────────────────────────────────────────────
st.subheader("Recent Orders")

try:
    orders = _fetch_orders(
        status=status_filter,
        limit=result_limit,
        symbols=symbols_param,
    )

    if orders:
        rows = []
        for o in orders:
            filled_price = o.get("filled_avg_price")
            rows.append(
                {
                    "Symbol": o.get("symbol", ""),
                    "Side": o.get("side", "").upper(),
                    "Qty": o.get("qty", ""),
                    "Filled Qty": o.get("filled_qty", "0"),
                    "Type": o.get("type", "").upper(),
                    "Fill Price": (
                        f"${float(filled_price):,.2f}" if filled_price else "—"
                    ),
                    "Status": o.get("status", ""),
                    "Submitted": _parse_timestamp(o.get("submitted_at")),
                    "Filled At": _parse_timestamp(o.get("filled_at")),
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            width="stretch",
            hide_index=True,
            column_config={
                "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                "Side": st.column_config.TextColumn("Side", width="small"),
                "Qty": st.column_config.TextColumn("Qty", width="small"),
                "Filled Qty": st.column_config.TextColumn("Filled", width="small"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Fill Price": st.column_config.TextColumn(
                    "Fill Price", width="small"
                ),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Submitted": st.column_config.TextColumn(
                    "Submitted", width="medium"
                ),
                "Filled At": st.column_config.TextColumn(
                    "Filled At", width="medium"
                ),
            },
        )

        filled = sum(1 for o in orders if o.get("status") == "filled")
        open_count = sum(
            1
            for o in orders
            if o.get("status")
            in ("new", "accepted", "pending_new", "partially_filled")
        )
        cancelled = sum(
            1
            for o in orders
            if o.get("status") in ("canceled", "expired", "rejected")
        )

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Orders", len(orders))
        with m2:
            st.metric("Filled", filled)
        with m3:
            st.metric("Open", open_count)
        with m4:
            st.metric("Cancelled / Rejected", cancelled)
    else:
        st.info("No orders found matching filters.")

except Exception as e:
    st.error(f"Failed to fetch orders: {e}")

st.divider()

# ── Fill History ──────────────────────────────────────────────────
st.subheader("Fill History")

try:
    fills = _fetch_fills(limit=result_limit)

    if symbols_param:
        fills = [f for f in fills if f.get("symbol") == symbols_param]

    if fills:
        fill_rows = []
        for f in fills:
            price = f.get("price")
            qty = f.get("qty")
            fill_rows.append(
                {
                    "Symbol": f.get("symbol", ""),
                    "Side": f.get("side", "").upper(),
                    "Qty": qty or "",
                    "Price": f"${float(price):,.2f}" if price else "—",
                    "Total": (
                        f"${float(price) * float(qty):,.2f}"
                        if price and qty
                        else "—"
                    ),
                    "Time": _parse_timestamp(f.get("transaction_time")),
                    "Order ID": (f.get("order_id", "")[:12] + "...")
                    if f.get("order_id")
                    else "—",
                }
            )

        st.dataframe(
            pd.DataFrame(fill_rows),
            width="stretch",
            hide_index=True,
            column_config={
                "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                "Side": st.column_config.TextColumn("Side", width="small"),
                "Qty": st.column_config.TextColumn("Qty", width="small"),
                "Price": st.column_config.TextColumn("Price", width="small"),
                "Total": st.column_config.TextColumn("Total", width="small"),
                "Time": st.column_config.TextColumn("Time", width="medium"),
                "Order ID": st.column_config.TextColumn(
                    "Order ID", width="medium"
                ),
            },
        )

        buy_fills = [f for f in fills if f.get("side") == "buy"]
        sell_fills = [f for f in fills if f.get("side") == "sell"]
        total_buy = sum(
            float(f.get("price", 0)) * float(f.get("qty", 0)) for f in buy_fills
        )
        total_sell = sum(
            float(f.get("price", 0)) * float(f.get("qty", 0)) for f in sell_fills
        )

        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.metric("Total Fills", len(fills))
        with f2:
            st.metric("Buys", len(buy_fills))
        with f3:
            st.metric("Sells", len(sell_fills))
        with f4:
            st.metric("Net Flow", f"${total_sell - total_buy:,.2f}")
    else:
        st.info("No fill activity found.")

except Exception as e:
    st.error(f"Failed to fetch fill activity: {e}")
