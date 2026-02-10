"""
Node: Retrieve chart / price documents from the chart vector store.
"""

from typing import Any, Dict

from trader_agent.graph.state import GraphState
from trader_agent.core.ingestion import chart_retriever


def retrieve_chart(state: GraphState) -> Dict[str, Any]:
    print("---RETRIEVE CHART---")
    ticker = state["ticker"]

    query = f"Recent OHLCV price data and summary for {ticker}"
    documents = chart_retriever.invoke(query)

    chart_texts = [doc.page_content for doc in documents]

    print(f"[RETRIEVE CHART] Got {len(chart_texts)} chart documents for {ticker}")
    return {"chart_documents": chart_texts}
