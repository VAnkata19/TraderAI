"""
News fetcher – uses Tavily API (via langchain-tavily) to search for
ticker-focused news articles and returns LangChain Document objects
ready for vector-store ingestion.
Falls back to RSS feeds if Tavily is not available.
"""

import re
from datetime import datetime
from html.parser import HTMLParser
from typing import List

import feedparser
import requests as _requests
from langchain_core.documents import Document

from config import DEFAULT_RSS_FEEDS, TAVILY_API_KEY

# ── Optional: langchain-tavily ───────────────────────────────────────────────
try:
    from langchain_tavily import TavilySearch
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("[WARN] langchain-tavily not installed – RSS fallback will be used.")


# ── Helpers ──────────────────────────────────────────────────────────────────

class _HTMLToTextParser(HTMLParser):
    """Strip HTML tags and return plain text."""
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        text = data.strip()
        if text:
            self._parts.append(text)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _get_company_name(ticker: str) -> str | None:
    """Look up a human-readable company name from Yahoo Finance."""
    try:
        resp = _requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": ticker, "quotesCount": 1, "newsCount": 0},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        resp.raise_for_status()
        quotes = resp.json().get("quotes", [])
        if quotes:
            q = quotes[0]
            return q.get("shortname") or q.get("longname")
    except Exception:
        pass
    return None


def _clean_html(raw: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    parser = _HTMLToTextParser()
    try:
        parser.feed(raw)
        text = parser.get_text()
    except Exception:
        text = re.sub(r"<[^>]+>", "", raw)
    return re.sub(r"\s+", " ", text).strip()


# ── Public entry point ───────────────────────────────────────────────────────

def fetch_news_for_ticker(
    ticker: str,
    rss_urls: List[str] | None = None,
) -> List[Document]:
    """Return news Documents for *ticker* (Tavily first, then RSS)."""
    if TAVILY_API_KEY and TAVILY_AVAILABLE:
        return _fetch_news_tavily(ticker)

    if not TAVILY_API_KEY:
        print("[NEWS] TAVILY_API_KEY not set – falling back to RSS")
    elif not TAVILY_AVAILABLE:
        print("[NEWS] langchain-tavily not installed – falling back to RSS")
    return _fetch_news_rss(ticker, rss_urls)


# ── Tavily path ──────────────────────────────────────────────────────────────

def _fetch_news_tavily(ticker: str) -> List[Document]:
    """Search news with TavilySearch (langchain-tavily)."""
    company_name = _get_company_name(ticker)
    label = f"{ticker} ({company_name})" if company_name else ticker
    print(f"[TAVILY] Fetching news for {label}")

    try:
        tool = TavilySearch(  # type: ignore[name-defined]
            max_results=10,
            topic="news",
            include_domains=[
                "yahoo.com", "reuters.com", "bloomberg.com",
                "cnbc.com", "seekingalpha.com", "marketwatch.com",
            ],
        )

        query = f"{company_name} {ticker} stock news" if company_name else f"{ticker} stock"
        response = tool.invoke({"query": query})
        results = response.get("results", []) if isinstance(response, dict) else []

        documents: List[Document] = []
        for r in results:
            title = r.get("title", "")
            content = r.get("content", "") or r.get("raw_content", "")
            url = r.get("url", "")
            published = r.get("published_date") or datetime.utcnow().isoformat()

            if not content or len(content) < 100:
                continue

            documents.append(
                Document(
                    page_content=f"Title: {title}\n\n{content}",
                    metadata={
                        "ticker": ticker,
                        "source": url,
                        "published": published,
                        "fetched_at": datetime.utcnow().isoformat(),
                    },
                )
            )

        print(f"[TAVILY] Fetched {len(documents)} articles for {ticker}")
        return documents

    except Exception as e:
        print(f"[TAVILY] Error: {e} – falling back to RSS")
        return _fetch_news_rss(ticker, None)


# ── RSS fallback ─────────────────────────────────────────────────────────────

def _fetch_news_rss(
    ticker: str,
    rss_urls: List[str] | None = None,
) -> List[Document]:
    """Fetch news via RSS feeds (used when Tavily is unavailable)."""
    urls = rss_urls or DEFAULT_RSS_FEEDS.get(ticker, [])
    if not urls:
        urls = [
            f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
            f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en",
        ]

    company_name = _get_company_name(ticker)
    label = f"{ticker} ({company_name})" if company_name else ticker
    print(f"[RSS] Fetching news for {label}")

    documents: List[Document] = []
    filtered_out = 0

    for url in urls:
        try:
            feed = feedparser.parse(url)
        except Exception as exc:
            print(f"[RSS] Failed to parse {url}: {exc}")
            continue

        for entry in feed.entries:
            title = str(entry.get("title", ""))
            summary = _clean_html(str(entry.get("summary", "")))
            link = str(entry.get("link", ""))
            published = str(entry.get("published", datetime.utcnow().isoformat()))

            if not summary:
                filtered_out += 1
                continue

            # Only keep articles that actually mention the ticker
            ticker_lower = ticker.lower()
            if ticker_lower not in title.lower() and ticker_lower not in summary.lower():
                filtered_out += 1
                continue

            documents.append(
                Document(
                    page_content=f"Title: {title}\n\n{summary}",
                    metadata={
                        "ticker": ticker,
                        "source": link,
                        "published": published,
                        "fetched_at": datetime.utcnow().isoformat(),
                    },
                )
            )

    print(f"[RSS] Fetched {len(documents)} articles for {ticker} ({filtered_out} filtered out)")
    return documents


