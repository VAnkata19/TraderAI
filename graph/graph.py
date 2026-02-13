"""
LangGraph workflow for the stock trading agent.

Pipeline: RETRIEVE_NEWS → RETRIEVE_CHART → RETRIEVE_PORTFOLIO → ANALYZE → EXECUTE_DECISION
"""

from langgraph.graph import END, StateGraph

from .consts import (
    RETRIEVE_NEWS,
    RETRIEVE_CHART,
    RETRIEVE_PORTFOLIO,
    ANALYZE,
    EXECUTE_DECISION,
)
from .nodes import (
    retrieve_news,
    retrieve_chart,
    retrieve_portfolio,
    analyze,
    execute_decision,
)
from .state import GraphState


# ── Build the graph ──────────────────────────────────────────────────────────
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node(RETRIEVE_NEWS, retrieve_news)
workflow.add_node(RETRIEVE_CHART, retrieve_chart)
workflow.add_node(RETRIEVE_PORTFOLIO, retrieve_portfolio)
workflow.add_node(ANALYZE, analyze)
workflow.add_node(EXECUTE_DECISION, execute_decision)

# Linear pipeline: news → chart → portfolio → analyze → execute → END
workflow.set_entry_point(RETRIEVE_NEWS)
workflow.add_edge(RETRIEVE_NEWS, RETRIEVE_CHART)
workflow.add_edge(RETRIEVE_CHART, RETRIEVE_PORTFOLIO)
workflow.add_edge(RETRIEVE_PORTFOLIO, ANALYZE)
workflow.add_edge(ANALYZE, EXECUTE_DECISION)
workflow.add_edge(EXECUTE_DECISION, END)

# Compile
app = workflow.compile()
