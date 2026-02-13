"""
Smoke tests for Alpaca broker functions.
Runs against your paper trading account — places real BUY and SELL orders.

Usage:
    pytest testing/alpacaAPI.py -v
    pytest testing/alpacaAPI.py -v -k test_buy
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.alpaca_broker import (
    get_account,
    get_positions,
    get_position,
    get_current_price,
    get_latest_quote,
    get_latest_trade,
    submit_market_order,
    get_orders,
    get_fill_activity,
)

TICKER = "AAPL"
QTY = 1


# ── Read-only tests (safe to run anytime) ────────────────────────────────────


class TestAccount:
    def test_get_account(self):
        acct = get_account()
        assert "equity" in acct
        assert "buying_power" in acct
        assert "cash" in acct
        assert float(acct["equity"]) >= 0

    def test_get_positions(self):
        positions = get_positions()
        assert isinstance(positions, list)

    def test_get_position_missing(self):
        pos = get_position("ZZZZZZ")
        assert pos is None


class TestMarketData:
    def test_get_current_price(self):
        price = get_current_price(TICKER)
        assert isinstance(price, float)
        assert price > 0

    def test_get_latest_quote(self):
        quote = get_latest_quote(TICKER)
        assert "bp" in quote or "ap" in quote

    def test_get_latest_trade(self):
        trade = get_latest_trade(TICKER)
        assert "p" in trade
        assert float(trade["p"]) > 0


class TestOrderHistory:
    def test_get_orders(self):
        orders = get_orders(status="all", limit=5)
        assert isinstance(orders, list)

    def test_get_orders_with_symbol_filter(self):
        orders = get_orders(status="all", limit=5, symbols=TICKER)
        assert isinstance(orders, list)
        for o in orders:
            assert o["symbol"] == TICKER

    def test_get_fill_activity(self):
        fills = get_fill_activity(limit=5)
        assert isinstance(fills, list)


# ── Order tests (place real paper trades) ─────────────────────────────────────


class TestBuySell:
    """These tests place real orders on your Alpaca paper account."""

    def test_buy_order(self):
        order = submit_market_order(TICKER, QTY, "buy")
        assert order["symbol"] == TICKER
        assert order["side"] == "buy"
        assert order["qty"] == str(QTY)
        assert order["status"] in ("accepted", "pending_new", "new", "filled")

    def test_sell_order(self):
        pos = get_position(TICKER)
        if not pos or float(pos.get("qty", 0)) <= 0:
            pytest.skip(f"No shares of {TICKER} to sell")
        order = submit_market_order(TICKER, QTY, "sell")
        assert order["symbol"] == TICKER
        assert order["side"] == "sell"
        assert order["qty"] == str(QTY)
        assert order["status"] in ("accepted", "pending_new", "new", "filled")
