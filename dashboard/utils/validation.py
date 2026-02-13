"""
API validation utilities for checking service connectivity.
"""

from config import OPENAI_API_KEY, DISCORD_WEBHOOK_URL


def is_openai_valid() -> bool:
    """Check if OpenAI API key is configured and valid."""
    if not OPENAI_API_KEY:
        return False
    
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        # Simple test call to verify API key works
        client.models.list()
        return True
    except Exception:
        return False


def is_discord_valid() -> bool:
    """Check if Discord webhook URL is configured and reachable.""" 
    if not DISCORD_WEBHOOK_URL:
        return False
        
    try:
        import requests
        # Simple GET to check if webhook URL is valid (won't send a message)
        response = requests.head(DISCORD_WEBHOOK_URL, timeout=5)
        return response.status_code in [200, 405]  # 405 is OK for webhooks
    except Exception:
        return False