"""
Backward compatibility hub for dashboard functionality.

This module imports all major functions from their new organized modules
to maintain backward compatibility while providing a clean modular structure.
"""

# Import all functions from the new modular structure
from dashboard.utils.models import (
    get_available_openai_models,
    estimate_tokens,
    estimate_cost_per_cycle,
    estimate_cost_per_day,
)

from dashboard.utils.storage import (
    load_custom_tickers,
    save_custom_tickers,
    load_decisions,
    save_decisions,
    load_actions_today,
    save_actions_today,
)

from dashboard.utils.validation import (
    is_openai_valid,
    is_discord_valid,
)

from dashboard.utils.data import (
    get_all_tickers,
    search_yahoo_tickers,
    get_ticker_data,
    get_ticker_info,
)

from dashboard.utils.charts import (
    create_candlestick_chart,
    create_mini_price_chart,
)

from dashboard.core.session import (
    init_session_state,
)

from dashboard.core.analysis import (
    start_analysis_loop,
    stop_analysis_loop,
    is_analysis_running,
    get_time_until_next_run,
)

# Legacy imports for backward compatibility
from pathlib import Path
ROOT = Path(__file__).parent.parent

# Export all for backward compatibility
__all__ = [
    # Models/OpenAI
    "get_available_openai_models",
    "estimate_tokens", 
    "estimate_cost_per_cycle",
    "estimate_cost_per_day",
    
    # Storage
    "load_custom_tickers",
    "save_custom_tickers",
    "load_decisions",
    "save_decisions", 
    "load_actions_today",
    "save_actions_today",
    
    # Validation
    "is_openai_valid",
    "is_discord_valid",
    
    # Session
    "init_session_state",
    
    # Data
    "get_all_tickers",
    "search_yahoo_tickers",
    "get_ticker_data",
    "get_ticker_info",
    
    # Charts
    "create_candlestick_chart",
    "create_mini_price_chart",
    
    # Analysis
    "start_analysis_loop",
    "stop_analysis_loop",
    "is_analysis_running", 
    "get_time_until_next_run",
    
    # Legacy
    "ROOT",
]