"""
Central configuration for the Trading Agent.
All tunables live here so they're easy to find and override via env vars.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent          # project root
CHROMA_NEWS_DIR = BASE_DIR / ".chroma_news"
CHROMA_CHART_DIR = BASE_DIR / ".chroma_chart"

# ── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# ── Tavily ───────────────────────────────────────────────────────────────────
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ── Discord ──────────────────────────────────────────────────────────────────
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ── Trading rules ────────────────────────────────────────────────────────────
MAX_ACTIONS_PER_DAY = int(os.getenv("MAX_ACTIONS_PER_DAY", "5"))
RUN_INTERVAL_SECONDS = int(os.getenv("RUN_INTERVAL_SECONDS", "300"))  # 5 minutes

# ── Tickers & RSS feeds ─────────────────────────────────────────────────────
# Comma-separated list of stock tickers to track
TICKERS = [t.strip() for t in os.getenv("TICKERS", "AAPL,MSFT,GOOGL").split(",")]

# RSS feeds per ticker – override via env or extend in code
# Format: {"AAPL": ["https://...rss1", "https://...rss2"], ...}
DEFAULT_RSS_FEEDS: dict[str, list[str]] = {
    "AAPL": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US",
    ],
    "MSFT": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=MSFT&region=US&lang=en-US",
    ],
    "GOOGL": [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GOOGL&region=US&lang=en-US",
    ],
}

# ── Chart data ───────────────────────────────────────────────────────────────
CHART_PERIOD = os.getenv("CHART_PERIOD", "5d")        # yfinance period
CHART_INTERVAL = os.getenv("CHART_INTERVAL", "5m")    # yfinance interval
