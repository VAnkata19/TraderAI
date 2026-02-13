"""
Chain configurations for the LLM analysis pipeline.

Defines the system prompts, input templates, and output types for each chain
in a data-driven format, enabling easy configuration changes without code modification.
"""

from dataclasses import dataclass
from typing import List, Literal, Optional, Type

from pydantic import BaseModel

from config import LLM_MODEL, LLM_TEMPERATURE


@dataclass
class ChainConfig:
    """Configuration for building an LLM chain."""

    name: str  # Chain identifier (e.g., "news_sentiment")
    system_prompt: str  # System message for the chain
    human_prompt_template: str  # Human message template with {variables}
    input_variables: List[str]  # Expected input variable names
    output_type: Literal["string", "structured"]  # Output parser type
    structured_model: Optional[Type[BaseModel]] = None  # Pydantic model for structured output
    llm_model: str = LLM_MODEL  # LLM model to use
    temperature: float = LLM_TEMPERATURE  # LLM temperature


# Chain configurations
NEWS_SENTIMENT_CONFIG = ChainConfig(
    name="news_sentiment",
    system_prompt=(
        "You are a financial news analyst specializing in sentiment analysis and impact assessment. "
        "Analyze the provided news articles to determine sentiment (bullish/bearish/neutral) and predict market impact. "
        "Focus on: 1) Direct impact on the stock, 2) Sector-wide implications, 3) Macro factors. "
        "Be concise and actionable."
    ),
    human_prompt_template=(
        "Ticker: {ticker}\n\n"
        "Recent news articles:\n"
        "{news_documents}\n\n"
        "Provide a brief sentiment analysis and market impact assessment."
    ),
    input_variables=["ticker", "news_documents"],
    output_type="string",
)

CHART_ANALYSIS_CONFIG = ChainConfig(
    name="chart_analysis",
    system_prompt=(
        "You are a technical analyst specializing in price action and chart patterns. "
        "Analyze the provided OHLCV data to identify trends, support/resistance levels, and potential breakouts. "
        "Focus on: 1) Trend direction, 2) Key levels, 3) Volume confirmation, 4) Momentum indicators. "
        "Be concise and focus on actionable levels."
    ),
    human_prompt_template=(
        "Ticker: {ticker}\n\n"
        "Historical price data:\n"
        "{chart_documents}\n\n"
        "Provide a brief technical analysis with key price levels and trend assessment."
    ),
    input_variables=["ticker", "chart_documents"],
    output_type="string",
)

# Import TradingDecision model for structured output
from graph.chains.trading_decision import TradingDecision

TRADING_DECISION_CONFIG = ChainConfig(
    name="trading_decision",
    system_prompt=(
        "You are an aggressive short-term trading decision agent. "
        "Based on sentiment, technical analysis, and portfolio context, make a trading decision. "
        "Decisions: BUY (if bullish catalyst), SELL (if bearish catalyst), HOLD (if uncertain). "
        "Be decisive and include confidence level (0.0-1.0). "
        "Consider: 1) News sentiment, 2) Technical setup, 3) Risk/reward, 4) Portfolio impact, 5) Daily action budget."
    ),
    human_prompt_template=(
        "Ticker: {ticker}\n\n"
        "--- News Sentiment Report ---\n"
        "{news_summary}\n\n"
        "--- Technical Analysis Report ---\n"
        "{chart_summary}\n\n"
        "--- Portfolio Context ---\n"
        "{portfolio_context}\n\n"
        "--- Action Budget ---\n"
        "Actions used today: {actions_today}/{max_actions}\n\n"
        "Make a trading decision and provide reasoning."
    ),
    input_variables=["ticker", "news_summary", "chart_summary", "portfolio_context", "actions_today", "max_actions"],
    output_type="structured",
    structured_model=TradingDecision,
)

# Registry of all chain configurations
CHAIN_CONFIGS = {
    "news_sentiment": NEWS_SENTIMENT_CONFIG,
    "chart_analysis": CHART_ANALYSIS_CONFIG,
    "trading_decision": TRADING_DECISION_CONFIG,
}
