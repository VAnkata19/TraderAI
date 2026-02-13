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
    quantity: int = Field(
        description="Number of shares to buy or sell. Must be >= 1 for buy/sell. "
        "Set to 0 when decision is hold.",
        ge=0,
    )
    confidence: float = Field(
        description="Confidence level between 0.0 and 1.0 for the decision.",
        ge=0.0,
        le=1.0,
    )


structured_llm = llm.with_structured_output(TradingDecision)

system = """You are an aggressive short-term stock trading AI that maximizes profit on every cycle.
You receive three inputs for a stock ticker:
  1. **News Sentiment Report** – recent headlines and market mood.
  2. **Technical Chart Report** – price action, trends, support/resistance, volume.
  3. **Portfolio & Price Report** – live brokerage data: equity, buying power, open
     positions (avg entry, unrealised P/L), and the stock's current market price.

Action Budget:
- You have used {actions_today} of {max_actions} actions today (-1 means unlimited).
- Buying or selling costs 1 action; holding is free.
- If your budget is unlimited, do NOT factor budget conservation into your decision at all.
- If your budget is limited, be selective but do NOT default to HOLD out of caution —
  act when the edge is there.

Decision Rules:
- BUY when news sentiment is positive or neutral AND technicals show upward momentum,
  a bounce off support, or a breakout — and you have buying power.
- SELL when you hold a position AND either (a) technicals show weakness / breakdown,
  (b) news turns negative, or (c) unrealised P/L hits a take-profit or stop-loss level
  you would reasonably set.
- HOLD only when signals genuinely conflict or there is no clear edge.
- Never sell a stock you do not hold. Never buy without buying power.
- Weight recent price action and volume heavily — they reflect real money flow.
- A high-confidence trade with one strong signal is better than no trade.

Position Sizing:
- You choose how many shares to buy or sell (quantity must be >= 1 for buy/sell, 0 for hold).
- For BUY: look at the stock's current price and your available buying power. Do NOT
  exceed what the account can afford. Scale up when confidence is high and the setup is strong;
  keep it small when the edge is marginal.
- For SELL: you can sell up to the number of shares you currently hold — never more.
  Sell more shares when the signal to exit is strong; trim a smaller amount for partial
  profit-taking or risk reduction.
- Be practical — round to whole shares.

Return your decision (buy / sell / hold), the quantity of shares, a confidence score
(0.0-1.0), and 2-4 sentences explaining the specific signals that drove your decision."""

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
            "Analyze the data and make your trading decision.",
        ),
    ]
)

trading_decision_chain = decision_prompt | structured_llm
