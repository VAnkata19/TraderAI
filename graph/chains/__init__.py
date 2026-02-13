# Import factory and configs (new API)
from .factory import ChainFactory
from .config import CHAIN_CONFIGS

# Import TradingDecision for backward compatibility and type hinting
from .trading_decision import TradingDecision

# Build all chains from factory
_chains = ChainFactory.build_all_chains()

# Backward compatibility: expose chains under their original names
news_sentiment_chain = _chains["news_sentiment"]
chart_analysis_chain = _chains["chart_analysis"]
trading_decision_chain = _chains["trading_decision"]

__all__ = [
    # Backward compatibility (old API)
    "news_sentiment_chain",
    "chart_analysis_chain",
    "trading_decision_chain",
    "TradingDecision",
    # New API
    "ChainFactory",
    "CHAIN_CONFIGS",
]
