"""
News sentiment analysis chain.
Takes retrieved news documents and produces a sentiment summary.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from config import LLM_MODEL, LLM_TEMPERATURE

llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)

system = """You are a financial news analyst specializing in stock market sentiment.
You will be given a collection of recent news articles about a specific stock ticker.

Your job:
1. Summarize the overall news sentiment (bullish / bearish / neutral).
2. Highlight the most impactful headlines and why they matter.
3. Note any upcoming catalysts (earnings, product launches, lawsuits, etc.).
4. Be concise but thorough – the output feeds into a trading decision model.

Respond with a structured sentiment report."""

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
