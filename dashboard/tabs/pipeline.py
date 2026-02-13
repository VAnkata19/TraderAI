"""
Tab: Pipeline — visualise the LangGraph workflow and decision rules.
"""

from pathlib import Path

import streamlit as st

from config import MAX_ACTIONS_PER_DAY



st.header("LangGraph Pipeline")

st.markdown(
    """
The trading agent follows a **linear pipeline** for each ticker:

```
RETRIEVE NEWS  →  RETRIEVE CHART  →  ANALYZE  →  EXECUTE DECISION
```
"""
)

pipeline_steps = [
    (
        "1️⃣  Retrieve News",
        "Queries the **news ChromaDB** collection for relevant articles about the ticker.",
    ),
    (
        "2️⃣  Retrieve Chart",
        "Queries the **chart ChromaDB** collection for recent OHLCV price data.",
    ),
    (
        "3️⃣  Analyze",
        "Runs **three LLM chains** sequentially:\n"
        "- **News Sentiment** — summarises headline sentiment\n"
        "- **Chart Technicals** — identifies trends and key levels\n"
        "- **Trading Decision** — produces BUY / SELL / HOLD with confidence",
    ),
    (
        "4️⃣  Execute Decision",
        "Checks the **daily action budget** and sends a **Discord notification** if a trade is executed.",
    ),
]

for title, desc in pipeline_steps:
    with st.expander(title, expanded=True):
        st.markdown(desc)

# Graph image
graph_path = (
    Path(__file__).resolve().parent.parent.parent.parent / "graph.png"
)
if graph_path.exists():
    st.divider()
    st.subheader("Pipeline Visualisation")
    st.image(str(graph_path), caption="LangGraph Pipeline")

st.divider()

st.subheader("Decision Rules")
st.markdown(
    f"""
| Rule | Detail |
|------|--------|
| **Actions** | BUY and SELL count as actions; HOLD does **not** |
| **Budget** | Max **{MAX_ACTIONS_PER_DAY}** actions per stock per day (resets at midnight UTC) |
| **Safety** | If budget exhausted, BUY/SELL is downgraded to HOLD |
| **Confidence** | Only trades when both news **and** chart signals align |
"""
)
