"""
News sentiment analysis chain.
Takes retrieved news documents and produces a sentiment summary.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from config import LLM_MODEL, LLM_TEMPERATURE

llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)

system = """You are a financial news analyst producing actionable sentiment reports for a trading bot.
You will be given recent news articles about a stock ticker.

Your report MUST include:
1. **Sentiment**: One word — Bullish, Bearish, or Neutral.
2. **Key Headlines**: The 2-3 most market-moving headlines with a one-line explanation of why each matters (earnings beat/miss, analyst upgrade/downgrade, product news, regulatory action, macro event).
3. **Catalysts**: Any upcoming events that could move the price (earnings date, FDA decision, product launch, legal ruling). If none, say "None identified."
4. **Trading Signal**: One sentence — what this news means for a short-term trade (e.g. "Positive sentiment supports a buy on any technical dip" or "Negative headline risk suggests caution").

Keep it concise. No filler. This feeds directly into an automated trading decision."""

news_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "Ticker: {ticker}\n\nNews articles:\n{news_documents}",
        ),
    ]
)

news_sentiment_chain = news_prompt | llm | StrOutputParser()
