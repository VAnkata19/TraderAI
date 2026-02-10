"""
Chart / price data fetcher – pulls OHLCV data from Yahoo Finance via yfinance
and converts it into LangChain Documents for ingestion into the chart vector DB.
"""

from datetime import datetime
from typing import List

import yfinance as yf
from langchain_core.documents import Document

from trader_agent.config import CHART_PERIOD, CHART_INTERVAL


def fetch_chart_for_ticker(ticker: str) -> List[Document]:
    """
    Download recent price data for *ticker* and convert each row (candle)
    into a Document.  The LLM will later consume these as context.

    If the raw DataFrame has more than ``MAX_CANDLES`` rows, we
    down-sample evenly so we never generate an excessive number of
    embedding requests.
    """
    MAX_CANDLES = 50

    tk = yf.Ticker(ticker)
    df = tk.history(period=CHART_PERIOD, interval=CHART_INTERVAL)

    if df.empty:
        print(f"[CHART] No data returned for {ticker}")
        return []

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

    # ── Summary document (latest stats) ──────────────────────────────────
    latest = full_df.iloc[-1]
    prev_close = full_df.iloc[-2]["Close"] if len(full_df) >= 2 else latest["Close"]
    change_pct = ((latest["Close"] - prev_close) / prev_close) * 100

    summary = (
        f"Ticker: {ticker} — Latest snapshot\n"
        f"Last Close: {latest['Close']:.4f}\n"
        f"Change: {change_pct:+.2f}%\n"
        f"Period High: {full_df['High'].max():.4f}\n"
        f"Period Low: {full_df['Low'].min():.4f}\n"
        f"Avg Volume: {int(full_df['Volume'].mean())}\n"
        f"Data range: {full_df.index[0]} → {full_df.index[-1]}"
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
