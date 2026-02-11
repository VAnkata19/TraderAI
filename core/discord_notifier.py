"""
Discord webhook notifier.
Sends trading decisions to a Discord channel.
"""

import requests

from config import DISCORD_WEBHOOK_URL


def send_discord_message(
    ticker: str,
    decision: str,
    reasoning: str,
    actions_today: int,
    max_actions: int,
) -> None:
    """
    Post a rich embed to Discord with the trading decision details.
    Silently skips if no webhook URL is configured.
    """
    if not DISCORD_WEBHOOK_URL:
        print("[DISCORD] No webhook URL configured – skipping notification")
        return

    color_map = {
        "buy": 0x2ECC71,   # green
        "sell": 0xE74C3C,  # red
        "hold": 0xF39C12,  # amber
    }

    embed = {
        "title": f"{'🟢 BUY' if decision == 'buy' else '🔴 SELL' if decision == 'sell' else '🟡 HOLD'}  —  {ticker}",
        "description": reasoning,
        "color": color_map.get(decision, 0x95A5A6),
        "fields": [
            {"name": "Decision", "value": decision.upper(), "inline": True},
            {"name": "Ticker", "value": ticker, "inline": True},
            {
                "name": "Actions today",
                "value": f"{actions_today} / {max_actions}",
                "inline": True,
            },
        ],
    }

    payload = {"embeds": [embed]}

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"[DISCORD] Notification sent for {ticker} ({decision})")
    except requests.RequestException as exc:
        print(f"[DISCORD] Failed to send notification: {exc}")
