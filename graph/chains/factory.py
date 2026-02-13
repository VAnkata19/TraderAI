"""
Factory for building LangChain chains from configuration.

Centralizes chain construction logic, making it easy to modify chain behavior
without changing multiple files.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

from .config import ChainConfig, CHAIN_CONFIGS


class ChainFactory:
    """Factory for building LangChain chains from configuration."""

    @staticmethod
    def build_chain(config: ChainConfig) -> Runnable:
        """
        Build a LangChain Runnable from configuration.

        Parameters:
            config: ChainConfig defining the chain

        Returns:
            Runnable (prompt | llm | parser)
        """
        # Initialize LLM with config settings
        llm = ChatOpenAI(model=config.llm_model, temperature=config.temperature)

        # Build prompt from template
        prompt = ChatPromptTemplate.from_messages([
            ("system", config.system_prompt),
            ("human", config.human_prompt_template),
        ])

        # Choose output parser based on config
        if config.output_type == "string":
            parser = StrOutputParser()
            return prompt | llm | parser
        elif config.output_type == "structured":
            # Use structured output with Pydantic model
            assert config.structured_model is not None, \
                f"structured_model required for structured output type in {config.name}"
            return prompt | llm.with_structured_output(config.structured_model)
        else:
            raise ValueError(f"Unknown output_type: {config.output_type}")

    @staticmethod
    def build_all_chains() -> dict[str, Runnable]:
        """
        Build all chains from CHAIN_CONFIGS registry.

        Returns:
            Dict mapping chain name to Runnable
        """
        return {
            name: ChainFactory.build_chain(config)
            for name, config in CHAIN_CONFIGS.items()
        }

    @staticmethod
    def build_chain_by_name(name: str) -> Runnable:
        """
        Build a single chain by name from registry.

        Parameters:
            name: Chain name from CHAIN_CONFIGS

        Returns:
            Runnable

        Raises:
            KeyError: If chain name not found in CHAIN_CONFIGS
        """
        if name not in CHAIN_CONFIGS:
            raise KeyError(f"Unknown chain: {name}. Available: {list(CHAIN_CONFIGS.keys())}")
        return ChainFactory.build_chain(CHAIN_CONFIGS[name])
