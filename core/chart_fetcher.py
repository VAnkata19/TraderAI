"""
Chart / price data fetcher – pulls OHLCV data from Alpaca API (with yfinance fallback)
and converts it into LangChain Documents for ingestion into the chart vector DB.
"""

from datetime import datetime, timezone, time
from typing import List

import pandas as pd
import yfinance as yf
from langchain_core.documents import Document

from config import CHART_PERIOD, CHART_INTERVAL, USE_ALPACA_DATA, USE_ALPACA_HISTORICAL
from core.alpaca_broker import get_historical_bars_alpaca


def get_market_status(latest_timestamp) -> str:
    """Determine if we're looking at pre-market, regular hours, or after-hours data."""
    # Convert to ET (market timezone)
    try:
        if latest_timestamp.tz is None:
            # Naive timestamp, assume it's already in ET
            et_time = latest_timestamp
        else:
            # Timezone-aware timestamp, convert to ET
            et_time = latest_timestamp.tz_convert('US/Eastern')
    except Exception:
        # Fallback - assume it's already in correct timezone
        et_time = latest_timestamp
    
    market_open = time(9, 30)  # 9:30 AM ET
    market_close = time(16, 0)  # 4:00 PM ET
    current_time = et_time.time()
    
    if current_time < market_open:
        return "Pre-market"
    elif current_time <= market_close:
        return "Regular hours"
    else:
        return "After-hours"


def fetch_chart_for_ticker(ticker: str) -> List[Document]:
    """
    Download recent price data for *ticker* and convert each row (candle)
    into a Document.  The LLM will later consume these as context.

    If the raw DataFrame has more than ``MAX_CANDLES`` rows, we
    down-sample evenly so we never generate an excessive number of
    embedding requests.
    
    Uses Alpaca API by default, falls back to yfinance if unavailable.
    """
    MAX_CANDLES = 50

    # Try Alpaca first if enabled, fallback to yfinance
    if USE_ALPACA_DATA and USE_ALPACA_HISTORICAL:
        try:
            print(f"[CHART] Fetching {ticker} data from Alpaca...")
            df = get_historical_bars_alpaca(ticker, CHART_PERIOD, CHART_INTERVAL)
            data_source = "Alpaca"
        except Exception as e:
            print(f"[CHART] Alpaca fetch failed for {ticker}: {e}")
            print(f"[CHART] Falling back to yfinance...")
            tk = yf.Ticker(ticker)
            # Include pre-market and after-hours data for most current information  
            df = tk.history(period=CHART_PERIOD, interval=CHART_INTERVAL, prepost=True)
            data_source = "yfinance (fallback)"
    else:
        if USE_ALPACA_DATA:
            print(f"[CHART] Using yfinance for {ticker} (Alpaca historical disabled - use free plan)")
        else:
            print(f"[CHART] Using yfinance for {ticker} (Alpaca disabled in config)")
        tk = yf.Ticker(ticker)
        # Include pre-market and after-hours data for most current information
        df = tk.history(period=CHART_PERIOD, interval=CHART_INTERVAL, prepost=True)
        data_source = "yfinance"

    if df.empty:
        print(f"[CHART] No data returned for {ticker}")
        return []

    print(f"[CHART] Successfully fetched {len(df)} candles for {ticker} from {data_source}")

    # Keep the full DataFrame for the summary, but downsample for per-candle docs
    full_df = df
    if len(df) > MAX_CANDLES:
        step = len(df) // MAX_CANDLES
        df = df.iloc[::step].tail(MAX_CANDLES)

    documents: List[Document] = []

    # ── Per-candle documents ─────────────────────────────────────────────
    for ts, row in df.iterrows():
        content = (
            f"Ticker: {ticker}\n"
            f"Timestamp: {ts}\n"
            f"Open: {row['Open']:.4f}\n"
            f"High: {row['High']:.4f}\n"
            f"Low: {row['Low']:.4f}\n"
            f"Close: {row['Close']:.4f}\n"
            f"Volume: {int(row['Volume'])}"
        )
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "ticker": ticker,
                    "timestamp": str(ts),
                    "fetched_at": datetime.utcnow().isoformat(),
                },
            )
        )

    # ─ Summary document (latest stats) ──────────────────────────────────
    latest = full_df.iloc[-1]
    prev_close = full_df.iloc[-2]["Close"] if len(full_df) >= 2 else latest["Close"]
    change_pct = ((latest["Close"] - prev_close) / prev_close) * 100
    
    # Get market status for context
    market_status = get_market_status(full_df.index[-1])

    summary = (
        f"Ticker: {ticker} — Latest snapshot (via {data_source})\n"
        f"Market Status: {market_status}\n"
        f"Last Close: {latest['Close']:.4f}\n"
        f"Change: {change_pct:+.2f}%\n"
        f"Period High: {full_df['High'].max():.4f}\n"
        f"Period Low: {full_df['Low'].min():.4f}\n"
        f"Avg Volume: {int(full_df['Volume'].mean())}\n"
        f"Data range: {full_df.index[0]} → {full_df.index[-1]}\n"
        f"Total candles: {len(full_df)}"
    )
    documents.append(
        Document(
            page_content=summary,
            metadata={
                "ticker": ticker,
                "type": "summary",
                "fetched_at": datetime.utcnow().isoformat(),
            },
        )
    )

    print(f"[CHART] Generated {len(documents)} documents for {ticker}")
    return documents
