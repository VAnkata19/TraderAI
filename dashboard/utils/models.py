"""
OpenAI model discovery and cost estimation utilities.
"""

import streamlit as st
from config import OPENAI_API_KEY, LLM_MODEL

# OpenAI pricing per 1M tokens (updated February 2026)
OPENAI_PRICING = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-2024-11-20": {"input": 5.00, "output": 15.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1-preview": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
}

_DEFAULT_PRICING = {"input": 5.00, "output": 15.00}  # safe fallback

# Sample prompt to estimate token usage
SAMPLE_PROMPT = """
News Summary:
- Apple's Q4 earnings beat expectations with record revenue
- iPhone 16 sales surge in Asia markets
- New AI features announced for next generation devices

Chart Information:
- Current Price: $195.00
- 5-day high: $198.50
- 5-day low: $192.00
- 52-week high: $210.00
- Volume: 52M shares

Based on this information, should we BUY, SELL, or HOLD this stock?
Please provide reasoning in 2-3 sentences.
"""


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_available_openai_models():
    """Get available OpenAI models dynamically."""
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        models = client.models.list()
        
        # Filter for chat models
        chat_models = []
        for model in models.data:
            model_id = model.id.lower()
            if any(prefix in model_id for prefix in ['gpt-', 'o1-']):
                # Exclude instruct models and fine-tuned versions
                if not any(suffix in model_id for suffix in ['-instruct', ':', 'ft-']):
                    chat_models.append(model.id)
        
        # Sort and prioritize common models
        priority_models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']
        available_models = []
        
        # Add priority models that exist
        for model in priority_models:
            if model in chat_models:
                available_models.append(model)
        
        # Add other models
        for model in sorted(chat_models):
            if model not in available_models:
                available_models.append(model)
                
        return available_models[:15]  # Limit to 15 models
        
    except Exception as e:
        print(f"Error fetching models: {e}")
        # Fallback to known models
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]


def estimate_tokens(text: str, model: str = LLM_MODEL) -> tuple[int, int] | None:
    """Estimate input/output tokens for a text prompt."""
    try:
        import tiktoken
        
        # Get the appropriate encoding for the model
        if model.startswith("gpt-4"):
            encoding_name = "cl100k_base"
        elif model.startswith("gpt-3.5"):
            encoding_name = "cl100k_base"
        else:
            encoding_name = "cl100k_base"  # fallback
            
        encoding = tiktoken.get_encoding(encoding_name)
        input_tokens = len(encoding.encode(text))
        
        # Conservative output estimate based on prompt type
        if "chart" in text.lower() or "price" in text.lower():
            output_tokens = 200  # Trading decisions usually brief
        else:
            output_tokens = int(input_tokens * 0.2)  # 20% of input length
            
        return input_tokens, output_tokens
        
    except Exception:
        return None  # tiktoken not available


def estimate_cost_per_cycle(model: str = LLM_MODEL) -> float:
    """Estimate cost in cents for one API call cycle using actual token counts."""
    # Use the provided model, fallback to configured LLM_MODEL, then gpt-4o
    if model not in OPENAI_PRICING:
        model = LLM_MODEL if LLM_MODEL in OPENAI_PRICING else "gpt-4o"
    pricing = OPENAI_PRICING.get(model, _DEFAULT_PRICING)
    
    # Try to use actual token estimates
    token_estimate = estimate_tokens(SAMPLE_PROMPT, model)
    if token_estimate:
        input_tokens, output_tokens = token_estimate
    else:
        # Fallback: use conservative estimates if tiktoken unavailable
        input_tokens = 2500
        output_tokens = 200
    
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cents = (input_cost + output_cost) * 100
    return total_cents


def estimate_cost_per_day(model: str = LLM_MODEL, run_interval_seconds: int = 300) -> float:
    """Estimate cost in cents for full day (24 hours)."""
    cycles_per_day = (24 * 60 * 60) / run_interval_seconds
    cost_per_cycle = estimate_cost_per_cycle(model)
    return cost_per_cycle * cycles_per_day