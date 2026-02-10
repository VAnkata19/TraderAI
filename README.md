# Trader Agent

LLM-powered stock trading agent built with **LangGraph**, **LangChain**, and **ChromaDB**.  
Now includes a **Streamlit dashboard** for real-time monitoring and on-demand analysis.

## How it works

```
Every 5 minutes:
  1. RSS feeds → fetch latest news → ingest into News Vector DB
  2. yfinance  → fetch OHLCV data  → ingest into Chart Vector DB
  3. LangGraph pipeline runs for each ticker:
       RETRIEVE NEWS → RETRIEVE CHART → ANALYZE → EXECUTE DECISION
  4. Discord webhook sends a notification with the decision + reasoning
```

### LangGraph Pipeline

| Node | What it does |
|---|---|
| **retrieve_news** | Queries the news Chroma collection for relevant articles |
| **retrieve_chart** | Queries the chart Chroma collection for recent price data |
| **analyze** | Runs 3 LLM chains: news sentiment → chart technicals → trading decision |
| **execute_decision** | Enforces the 5-action daily budget, sends Discord alert |

### Decision Rules
- The LLM outputs one of: **BUY**, **SELL**, or **HOLD**
- **HOLD** does **not** count towards the daily action limit
- Max **5 actions** (buy/sell) per day (configurable)
- If the budget is exhausted, buy/sell is downgraded to hold

## Setup

### 1. Environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Optional overrides
TICKERS=AAPL,MSFT,GOOGL
MAX_ACTIONS_PER_DAY=5
RUN_INTERVAL_SECONDS=300
LLM_MODEL=gpt-4o
```

### 2. Install dependencies

```bash
pip install -e .
# or
uv pip install -e .
```

### 3. Run the agent (CLI scheduler)

```bash
python -m trader_agent.main
# or if installed via pip:
trader-agent
```

### 4. Run the Streamlit dashboard

```bash
streamlit run trader_agent/dashboard/app.py
```

The dashboard provides:
- **Market Overview** — live price cards for all tracked tickers
- **On-demand Analysis** — trigger the full LangGraph pipeline from the UI
- **News Feed** — browse fetched RSS articles per ticker
- **Interactive Charts** — candlestick & line charts with configurable timeframes
- **Pipeline Viewer** — visualise the LangGraph workflow and decision rules

## Project Structure

```
trader_agent/
├── __init__.py
├── config.py                  # All tunables & env var loading
├── main.py                    # CLI scheduler loop entry point
│
├── core/                      # Data fetching, ingestion & notifications
│   ├── rss_fetcher.py         #   Pulls news via RSS (feedparser)
│   ├── chart_fetcher.py       #   Pulls OHLCV via yfinance
│   ├── ingestion.py           #   Two Chroma vector stores (news + chart)
│   └── discord_notifier.py    #   Sends rich embeds to Discord webhook
│
├── graph/                     # LangGraph trading pipeline
│   ├── consts.py              #   Node name constants
│   ├── state.py               #   GraphState TypedDict
│   ├── graph.py               #   LangGraph workflow definition
│   ├── chains/
│   │   ├── news_analyzer.py   #     News sentiment chain
│   │   ├── chart_analyzer.py  #     Technical analysis chain
│   │   └── trading_decision.py#     BUY/SELL/HOLD structured output chain
│   └── nodes/
│       ├── retrieve_news.py   #     Queries news vector store
│       ├── retrieve_chart.py  #     Queries chart vector store
│       ├── analyze.py         #     Runs all 3 chains
│       └── execute_decision.py#     Budget check + Discord notify
│
└── dashboard/                 # Streamlit web UI
    └── app.py                 #   Interactive dashboard
```
