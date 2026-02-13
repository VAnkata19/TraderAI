"""Abstract base class for LLM context builders."""

from abc import ABC, abstractmethod


class ContextBuilder(ABC):
    """Abstract base for building LLM context from various data sources.

    Context builders transform raw market/account data into natural language strings
    suitable for consumption by LLM prompts. This separation enables:
    - Decoupling data fetching from prompt engineering
    - Easy testing and modification of context formatting
    - Reuse across different LLM chains
    """

    @abstractmethod
    def build(self, ticker: str) -> str:
        """Build context string for a given ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Formatted context string for LLM consumption
        """
        pass
