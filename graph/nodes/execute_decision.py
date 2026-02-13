"""
Node: Execute the trading decision.
- If decision is "hold" → do nothing, mark as not executed.
- If decision is "buy" or "sell" → check action budget, place order via Alpaca,
  send Discord alert.
"""

from typing import Any, Dict

from graph.state import GraphState
from core.discord_notifier import send_discord_message
from core.alpaca import (
    submit_market_order,
    get_current_price,
    get_position,
)


def execute_decision(state: GraphState) -> Dict[str, Any]:
    print("---EXECUTE DECISION---")
    ticker = state["ticker"]
    decision = state["decision"].lower().strip()
    reasoning = state["reasoning"]
    actions_today = state["actions_today"]
    max_actions = state["max_actions"]

    # Hold never costs an action
    if decision == "hold":
        print(f"[EXECUTE] {ticker}: HOLD – no action taken")
        return {"executed": False, "order_result": ""}

    # Buy / Sell: check daily budget (-1 means unlimited)
    if max_actions != -1 and actions_today >= max_actions:
        msg = (
            f"Action budget exhausted ({actions_today}/{max_actions}). "
            f"Wanted to {decision.upper()} but converting to HOLD."
        )
        print(f"[EXECUTE] {ticker}: {msg}")
        return {"executed": False, "decision": "hold", "reasoning": msg, "order_result": ""}

    # Use the quantity chosen by the LLM (minimum 1 for buy/sell)
    qty = max(state.get("quantity", 1), 1)

    # For SELL: verify we actually hold a position and cap qty to held shares
    if decision == "sell":
        pos = get_position(ticker)
        if not pos or float(pos.get("qty", 0)) <= 0:
            msg = f"Cannot SELL {ticker} – no open position. Converting to HOLD."
            print(f"[EXECUTE] {ticker}: {msg}")
            return {"executed": False, "decision": "hold", "reasoning": msg, "order_result": ""}
        held = int(float(pos["qty"]))
        if qty > held:
            print(f"[EXECUTE] {ticker}: LLM requested {qty} shares but only hold {held} — capping")
            qty = held
    order_summary = ""
    try:
        price_before = get_current_price(ticker)
        order = submit_market_order(ticker, qty, decision)
        order_id = order.get("id", "unknown")
        order_status = order.get("status", "unknown")
        order_summary = (
            f"Order {order_id}: {decision.upper()} {qty} share(s) of {ticker} "
            f"@ ~${price_before:,.2f} | Status: {order_status}"
        )
        print(f"[EXECUTE] {ticker}: {decision.upper()} executed via Alpaca ✓  ({order_summary})")
    except Exception as e:
        order_summary = f"Alpaca order FAILED: {e}"
        print(f"[EXECUTE] {ticker}: ❌ Alpaca order failed – {e}")
        return {"executed": False, "order_result": order_summary}

    # ── Notify Discord ───────────────────────────────────────────────────
    send_discord_message(
        ticker=ticker,
        decision=decision,
        reasoning=f"{reasoning}\n\n📋 {order_summary}",
        actions_today=actions_today + 1,
        max_actions=max_actions,
    )
    return {
        "executed": True,
        "actions_today": actions_today + 1,
        "order_result": order_summary,
    }
