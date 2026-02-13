"""
Data fetching and ticker management utilities using provider chains.
"""

import pandas as pd
import streamlit as st
from config import TICKERS
from dashboard.utils.storage import load_custom_tickers
from core.providers.chains import get_historical_bars_chain, get_ticker_info_chain
from core.alpaca import clear_alpaca_cache


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
    """Get OHLCV data for ticker using configured provider chain (Alpaca → yfinance)."""
    chain = get_historical_bars_chain()
    return chain.get_historical_bars(ticker, period, interval)


def clear_data_cache():
    """Clear all cached data to force fresh fetches."""
    # Clear Streamlit cache
    if hasattr(st, 'cache_data'):
        try:
            st.cache_data.clear()
        except Exception:
            pass

    # Clear Alpaca cache
    try:
        clear_alpaca_cache()
        return True
    except Exception:
        pass

    return False


@st.cache_data(ttl=60)
def get_ticker_info(ticker: str) -> dict | None:
    """Get current ticker info (price, change, etc.) using configured provider chain."""
    chain = get_ticker_info_chain()
    return chain.get_ticker_info(ticker)