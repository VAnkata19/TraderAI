"""
Node: Execute the trading decision.
- If decision is "hold" → do nothing, mark as not executed.
- If decision is "buy" or "sell" → check action budget, send Discord alert.
"""

from typing import Any, Dict

from trader_agent.graph.state import GraphState
from trader_agent.core.discord_notifier import send_discord_message


def execute_decision(state: GraphState) -> Dict[str, Any]:
    print("---EXECUTE DECISION---")
    ticker = state["ticker"]
    decision = state["decision"]
    reasoning = state["reasoning"]
    actions_today = state["actions_today"]
    max_actions = state["max_actions"]

    # Hold never costs an action
    if decision == "hold":
        print(f"[EXECUTE] {ticker}: HOLD – no action taken")
        return {"executed": False}

    # Buy / Sell: check daily budget
    if actions_today >= max_actions:
        msg = (
            f"Action budget exhausted ({actions_today}/{max_actions}). "
            f"Wanted to {decision.upper()} but converting to HOLD."
        )
        print(f"[EXECUTE] {ticker}: {msg}")
        return {"executed": False, "decision": "hold", "reasoning": msg}

    # Budget OK – execute
    print(f"[EXECUTE] {ticker}: {decision.upper()} executed ✓")
    send_discord_message(
        ticker=ticker,
        decision=decision,
        reasoning=reasoning,
        actions_today=actions_today + 1,
        max_actions=max_actions,
    )
    return {"executed": True, "actions_today": actions_today + 1}
