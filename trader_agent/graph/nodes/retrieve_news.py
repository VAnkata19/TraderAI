"""
Node: Retrieve news documents from the news vector store for the given ticker.
"""

from typing import Any, Dict

from trader_agent.graph.state import GraphState
from trader_agent.core.ingestion import news_retriever


def retrieve_news(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE NEWS---")
    ticker = state["ticker"]

    # Query the news vector store with the ticker as the search query
    query = f"Latest news and events for {ticker} stock"
    documents = news_retriever.invoke(query)

    # Convert to string representations for the LLM
    news_texts = [doc.page_content for doc in documents]

    print(f"[RETRIEVE NEWS] Got {len(news_texts)} news documents for {ticker}")
    return {"news_documents": news_texts}
