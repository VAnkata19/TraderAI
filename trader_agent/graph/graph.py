"""
LangGraph workflow for the stock trading agent.

Pipeline: RETRIEVE_NEWS → RETRIEVE_CHART → ANALYZE → EXECUTE_DECISION
"""

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import END, StateGraph

from .consts import (
    RETRIEVE_NEWS,
    RETRIEVE_CHART,
    ANALYZE,
    EXECUTE_DECISION,
)
from .nodes import (
    retrieve_news,
    retrieve_chart,
    analyze,
    execute_decision,
)
from .state import GraphState


# ── Build the graph ──────────────────────────────────────────────────────────
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node(RETRIEVE_NEWS, retrieve_news)
workflow.add_node(RETRIEVE_CHART, retrieve_chart)
workflow.add_node(ANALYZE, analyze)
workflow.add_node(EXECUTE_DECISION, execute_decision)

# Linear pipeline: news → chart → analyze → execute → END
workflow.set_entry_point(RETRIEVE_NEWS)
workflow.add_edge(RETRIEVE_NEWS, RETRIEVE_CHART)
workflow.add_edge(RETRIEVE_CHART, ANALYZE)
workflow.add_edge(ANALYZE, EXECUTE_DECISION)
workflow.add_edge(EXECUTE_DECISION, END)

# Compile
app = workflow.compile()

# Optionally export the graph visualisation
try:
    app.get_graph().draw_mermaid_png(output_file_path="graph.png")
except Exception:
    pass  # non-critical – skip if mermaid rendering unavailable
