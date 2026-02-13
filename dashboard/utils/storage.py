"""
File storage and persistence utilities for the dashboard.
"""

import json
from datetime import datetime
from pathlib import Path

# ── Persistent Storage ──────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent.parent  # Go up to project root
_DATA_DIR = _ROOT / "data"
_DATA_DIR.mkdir(exist_ok=True)
_TICKERS_FILE = _DATA_DIR / "tickers.json"
_DECISIONS_FILE = _DATA_DIR / "decisions.json"
_ACTIONS_TODAY_FILE = _DATA_DIR / "actions_today.json"


def load_tickers() -> list[str]:
    """Load all tickers from persistent storage."""
    if _TICKERS_FILE.exists():
        try:
            with open(_TICKERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_tickers(tickers: list[str]) -> None:
    """Save all tickers to persistent storage."""
    with open(_TICKERS_FILE, "w") as f:
        json.dump(tickers, f)


def load_decisions() -> list[dict]:
    """Load trading decisions from persistent storage."""
    if _DECISIONS_FILE.exists():
        try:
            with open(_DECISIONS_FILE, "r") as f:
                decisions = json.load(f)

            # Filter recent decisions (last 30 days)
            cutoff = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            recent_decisions = []

            for d in decisions:
                try:
                    # Parse ISO format timestamp string
                    timestamp_str = d.get("timestamp", "")
                    ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).timestamp()
                    if ts > cutoff:
                        recent_decisions.append(d)
                except (ValueError, AttributeError):
                    # If timestamp is invalid, include the decision anyway
                    recent_decisions.append(d)

            return recent_decisions
        except Exception:
            pass
    return []


def save_decisions(decisions: list[dict]) -> None:
    """Save trading decisions to persistent storage."""
    # Keep only last 1000 decisions to avoid file bloat
    if len(decisions) > 1000:
        decisions = decisions[-1000:]
    
    with open(_DECISIONS_FILE, "w") as f:
        json.dump(decisions, f, indent=2)


def load_actions_today() -> dict[str, int]:
    """Load today's action counts from persistent storage."""
    if _ACTIONS_TODAY_FILE.exists():
        try:
            with open(_ACTIONS_TODAY_FILE, "r") as f:
                data = json.load(f)
            
            # Check if it's from today
            file_date = data.get("date", "")
            today = datetime.now().strftime("%Y-%m-%d")
            
            if file_date == today:
                return data.get("actions", {})
        except Exception:
            pass
    
    # Return empty dict if file doesn't exist or is old
    return {}


def save_actions_today(actions: dict[str, int]) -> None:
    """Save today's action counts to persistent storage."""
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "actions": actions,
        "saved_at": datetime.now().isoformat(),
    }
    
    with open(_ACTIONS_TODAY_FILE, "w") as f:
        json.dump(data, f, indent=2)