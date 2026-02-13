"""
Chart / technical analysis chain.
Takes retrieved OHLCV documents and produces a technical summary.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from config import LLM_MODEL, LLM_TEMPERATURE

llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)

system = """You are a technical analyst producing actionable chart reports for a trading bot.
You will be given recent OHLCV (Open, High, Low, Close, Volume) candle data for a stock.

Your report MUST include:
1. **Trend**: One word — Uptrend, Downtrend, or Sideways. Then one sentence on why (e.g. higher highs/lows, breakdown below support).
2. **Key Levels**: The nearest support and resistance prices visible in the data.
3. **Volume**: Is volume confirming the trend? Note any unusual spikes or divergences.
4. **Momentum**: Is the move accelerating or fading? Look at the size and direction of recent candles vs earlier ones.
5. **Trading Signal**: One sentence — what the chart says to do right now (e.g. "Price bouncing off support with rising volume — favors a buy" or "Breakdown below support on high volume — favors a sell").

Keep it concise. No filler. This feeds directly into an automated trading decision."""

chart_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "Ticker: {ticker}\n\nChart data:\n{chart_documents}",
        ),
    ]
)

chart_analysis_chain = chart_prompt | llm | StrOutputParser()
