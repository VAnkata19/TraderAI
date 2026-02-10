"""
Vector-store ingestion for the trading agent.

Two separate Chroma collections:
  • **news-store**  – articles fetched via RSS
  • **chart-store** – OHLCV candle data from yfinance

Call ``ingest_news`` / ``ingest_chart`` to upsert new documents, and use
the module-level ``news_retriever`` / ``chart_retriever`` to query them.
"""

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from typing import List

from trader_agent.config import CHROMA_NEWS_DIR, CHROMA_CHART_DIR

embeddings = OpenAIEmbeddings()

_BATCH_SIZE = 10  # Smaller batch size to avoid memory issues

# ── News vector store ────────────────────────────────────────────────────────
news_vectorstore = Chroma(
    collection_name="news-store",
    persist_directory=str(CHROMA_NEWS_DIR),
    embedding_function=embeddings,
)

news_retriever = news_vectorstore.as_retriever(
    search_kwargs={"k": 8},
)


def ingest_news(documents: List[Document]) -> None:
    """Add news documents into the news vector store with error handling."""
    if not documents:
        return
    
    successful = 0
    failed = 0
    
    for i in range(0, len(documents), _BATCH_SIZE):
        batch = documents[i : i + _BATCH_SIZE]
        try:
            news_vectorstore.add_documents(batch)
            successful += len(batch)
            print(f"[INGEST] ✓ Added batch {i // _BATCH_SIZE + 1}: {len(batch)} news docs")
        except Exception as e:
            failed += len(batch)
            print(f"[INGEST] ⚠️  Failed to add batch {i // _BATCH_SIZE + 1}: {e}")
    
    print(f"[INGEST] News complete: {successful} added, {failed} failed")


# ── Chart vector store ───────────────────────────────────────────────────────
chart_vectorstore = Chroma(
    collection_name="chart-store",
    persist_directory=str(CHROMA_CHART_DIR),
    embedding_function=embeddings,
)

chart_retriever = chart_vectorstore.as_retriever(
    search_kwargs={"k": 10},
)


def ingest_chart(documents: List[Document]) -> None:
    """Add chart documents into the chart vector store with error handling."""
    if not documents:
        return
    
    successful = 0
    failed = 0
    
    for i in range(0, len(documents), _BATCH_SIZE):
        batch = documents[i : i + _BATCH_SIZE]
        try:
            chart_vectorstore.add_documents(batch)
            successful += len(batch)
            print(f"[INGEST] ✓ Added batch {i // _BATCH_SIZE + 1}: {len(batch)} chart docs")
        except Exception as e:
            failed += len(batch)
            print(f"[INGEST] ⚠️  Failed to add batch {i // _BATCH_SIZE + 1}: {e}")
    
    print(f"[INGEST] Chart complete: {successful} added, {failed} failed")
