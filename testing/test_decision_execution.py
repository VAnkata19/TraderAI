"""
Integration tests for the LLM decision → Alpaca execution pipeline.

Verifies that when the execute_decision node receives a BUY or SELL decision,
the order actually goes through Alpaca's paper trading API.

Usage:
    pytest testing/test_decision_execution.py -v
    pytest testing/test_decision_execution.py -v -k test_buy_decision
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from graph.nodes.execute_decision import execute_decision
from core.alpaca import get_position, get_orders

TICKER = "AAPL"


def _make_state(decision: str, quantity: int = 1, actions_today: int = 0, max_actions: int = 5):
    """Build a minimal GraphState dict for execute_decision."""
    return {
        "ticker": TICKER,
        "news_documents": [],
        "chart_documents": [],
        "news_summary": "Test news summary.",
        "chart_summary": "Test chart summary.",
        "portfolio_context": "Test portfolio context.",
        "decision": decision,
        "quantity": quantity,
        "reasoning": f"Test reasoning for {decision}.",
        "actions_today": actions_today,
        "max_actions": max_actions,
        "executed": False,
        "order_result": "",
    }


# ── BUY decision tests ──────────────────────────────────────────────────────


class TestBuyDecision:
    """Verify a BUY decision flows through to Alpaca."""

    def test_buy_decision_places_order(self):
        state = _make_state("buy")
        result = execute_decision(state)

        assert result["executed"] is True
        assert result["actions_today"] == 1
        assert "BUY" in result["order_result"]
        assert TICKER in result["order_result"]

    def test_buy_decision_reflected_in_orders(self):
        state = _make_state("buy")
        result = execute_decision(state)

        assert result["executed"] is True

        orders = get_orders(status="all", limit=1, symbols=TICKER)
        assert len(orders) >= 1
        latest = orders[0]
        assert latest["symbol"] == TICKER
        assert latest["side"] == "buy"

    def test_buy_blocked_when_budget_exhausted(self):
        state = _make_state("buy", actions_today=5, max_actions=5)
        result = execute_decision(state)

        assert result["executed"] is False
        assert result.get("decision") == "hold"


# ── SELL decision tests ──────────────────────────────────────────────────────


class TestSellDecision:
    """Verify a SELL decision flows through to Alpaca."""

    def test_sell_decision_places_order(self):
        pos = get_position(TICKER)
        if not pos or float(pos.get("qty", 0)) <= 0:
            pytest.skip(f"No shares of {TICKER} to sell — run a buy test first")

        state = _make_state("sell")
        result = execute_decision(state)

        assert result["executed"] is True
        assert result["actions_today"] == 1
        assert "SELL" in result["order_result"]
        assert TICKER in result["order_result"]

    def test_sell_decision_reflected_in_orders(self):
        pos = get_position(TICKER)
        if not pos or float(pos.get("qty", 0)) <= 0:
            pytest.skip(f"No shares of {TICKER} to sell")

        state = _make_state("sell")
        result = execute_decision(state)

        assert result["executed"] is True

        orders = get_orders(status="all", limit=1, symbols=TICKER)
        assert len(orders) >= 1
        latest = orders[0]
        assert latest["symbol"] == TICKER
        assert latest["side"] == "sell"

    def test_sell_blocked_when_no_position(self):
        state = _make_state("sell")
        state["ticker"] = "ZZZZZZ"
        result = execute_decision(state)

        assert result["executed"] is False
        assert result.get("decision") == "hold"

    def test_sell_blocked_when_budget_exhausted(self):
        state = _make_state("sell", actions_today=5, max_actions=5)
        result = execute_decision(state)

        assert result["executed"] is False
        assert result.get("decision") == "hold"


# ── HOLD decision tests ─────────────────────────────────────────────────────


class TestHoldDecision:
    """Verify a HOLD decision does NOT place any order."""

    def test_hold_does_not_execute(self):
        state = _make_state("hold")
        result = execute_decision(state)

        assert result["executed"] is False
        assert result["order_result"] == ""

    def test_hold_does_not_consume_budget(self):
        state = _make_state("hold", actions_today=2, max_actions=5)
        result = execute_decision(state)

        assert result["executed"] is False
        assert "actions_today" not in result  # hold doesn't touch the counter
