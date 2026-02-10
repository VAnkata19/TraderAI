"""
Chart / technical analysis chain.
Takes retrieved OHLCV documents and produces a technical summary.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from trader_agent.config import LLM_MODEL, LLM_TEMPERATURE

llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)

system = """You are a professional technical analyst with deep experience reading price-action data.
You will be given recent OHLCV (Open, High, Low, Close, Volume) candle data for a stock.

Your job:
1. Identify the current short-term trend (uptrend / downtrend / sideways).
2. Note significant support and resistance levels visible in the data.
3. Comment on volume dynamics (increasing, decreasing, unusual spikes).
4. Provide a brief technical outlook (bullish / bearish / neutral).
5. Be concise — the output feeds into a trading decision model.

Respond with a structured technical report."""

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
