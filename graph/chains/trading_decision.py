"""
Core trading-decision chain.
Consumes the news sentiment summary + chart technical summary + live portfolio
data from Alpaca and outputs a structured decision: BUY / SELL / HOLD with reasoning.
"""

from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import LLM_MODEL, LLM_TEMPERATURE

llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)


class TradingDecision(BaseModel):
    """Structured output for the trading decision."""

    decision: Literal["buy", "sell", "hold"] = Field(
        description="The trading action to take: buy, sell, or hold."
    )
    reasoning: str = Field(
        description="A clear 2-4 sentence explanation of why this decision was made, "
        "referencing news sentiment, technical signals, and portfolio context."
    )
    confidence: float = Field(
        description="Confidence level between 0.0 and 1.0 for the decision.",
        ge=0.0,
        le=1.0,
    )


structured_llm = llm.with_structured_output(TradingDecision)

system = """You are an expert stock trading AI agent making careful, deliberate decisions.
You are given three analysis inputs for a particular stock ticker:
  1. A **news sentiment report** – summarises recent headlines and market mood.
  2. A **technical chart report** – summarises price action, trends, and volume.
  3. A **portfolio & price report** – live data from your brokerage account including
     your current equity, buying power, any open position in this stock (with avg entry
     price and unrealised P/L), and the stock's current market price.

Decision-Making Rules:
- You have a limited number of actions per day (buying or selling count as actions; holding does not).
- You have already used {actions_today} out of {max_actions} actions today.
- Only recommend BUY or SELL when you have strong conviction from BOTH news and chart data,
  AND the portfolio context supports the trade (e.g. you have buying power to buy, or you
  hold shares to sell).
- When deciding to SELL, you should only sell if you currently hold a position in the stock.
- When deciding to BUY, verify you have enough buying power.
- Consider unrealised P/L when deciding whether to hold or take profit / cut losses.
- If signals are mixed or weak, prefer HOLD to preserve action budget.
- Never recommend an action just to use up your budget.
- Choose carefully – make each decision with clear evidence from all three reports.

Return your decision (buy / sell / hold), a confidence score (0.0-1.0), and a concise
reasoning focused on what triggered your decision."""

decision_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "Ticker: {ticker}\n\n"
            "--- News Sentiment Report ---\n{news_summary}\n\n"
            "--- Technical Chart Report ---\n{chart_summary}\n\n"
            "--- Portfolio & Price Report ---\n{portfolio_context}\n\n"
            "Actions used today: {actions_today} / {max_actions}\n\n"
            "What is your trading decision?",
        ),
    ]
)

trading_decision_chain = decision_prompt | structured_llm
