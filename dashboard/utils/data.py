"""
Data fetching and ticker management utilities.
"""

import pandas as pd
import streamlit as st
import yfinance as yf
from config import TICKERS, USE_ALPACA_DATA, USE_ALPACA_HISTORICAL
from dashboard.utils.storage import load_custom_tickers


def get_all_tickers() -> list[str]:
    """Get all tickers: configured + custom ones."""
    custom = load_custom_tickers()
    all_tickers = list(TICKERS) + custom
    return sorted(set(all_tickers))  # Remove duplicates and sort


def search_yahoo_tickers(query: str) -> list[dict]:
    """Search for ticker symbols using Yahoo Finance."""
    if len(query) < 1:
        return []
        
    try:
        import yfinance as yf
        import requests
        
        # Use Yahoo's search endpoint
        url = f"https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotesCount": 10, "newsCount": 0}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        quotes = data.get("quotes", [])
        
        results = []
        for quote in quotes[:10]:  # Limit to 10 results
            if quote.get("typeDisp") in ["Equity", "ETF"]:  # Only stocks and ETFs
                results.append({
                    "symbol": quote.get("symbol", ""),
                    "name": quote.get("shortname", quote.get("longname", "")),
                    "exchange": quote.get("exchange", ""),
                })
        
        return results
        
    except Exception as e:
        print(f"Search error: {e}")
        return []


def get_ticker_data(ticker: str, period: str = "5d", interval: str = "5m") -> pd.DataFrame:
    """Get OHLCV data for ticker, using Alpaca with yfinance fallback."""
    if USE_ALPACA_DATA and USE_ALPACA_HISTORICAL:
        try:
            from core.alpaca_broker import get_historical_bars_alpaca
            return get_historical_bars_alpaca(ticker, period, interval)
        except Exception as e:
            print(f"[DASHBOARD] Alpaca data fetch failed: {e}, using yfinance")
            # Include pre-market and after-hours for complete picture
            return yf.Ticker(ticker).history(period=period, interval=interval, prepost=True)
    else:
        # Include pre-market and after-hours for complete picture
        return yf.Ticker(ticker).history(period=period, interval=interval, prepost=True)


@st.cache_data(ttl=60)
def get_ticker_info(ticker: str) -> dict | None:
    """Get current ticker info (price, change, etc.) using Alpaca with yfinance fallback."""
    if USE_ALPACA_DATA:
        try:
            from core.alpaca_broker import get_ticker_info_alpaca
            return get_ticker_info_alpaca(ticker)
        except Exception as e:
            print(f"[DASHBOARD] Alpaca ticker info failed: {e}, using yfinance")
    
    # Fallback to yfinance
    try:
        info = yf.Ticker(ticker).fast_info
        prev = info.previous_close
        last = info.last_price
        
        if last is None or prev is None:
            return None
            
        return {
            "price": last,
            "prev_close": prev,
            "change": last - prev,
            "change_pct": ((last - prev) / prev) * 100 if prev else 0,
        }
    except Exception:
        return None