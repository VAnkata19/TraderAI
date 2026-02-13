"""
Orchestration layer for LLM chain execution with timeout and error handling.

Supports both parallel and sequential execution of chains with configurable timeouts,
error handling, and fallback values.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

from langchain_core.runnables import Runnable


@dataclass
class ChainExecutionConfig:
    """Configuration for executing a single LLM chain."""

    name: str  # Chain name (e.g., "news_sentiment", "chart_analysis")
    timeout: float = 30.0  # Timeout in seconds
    fallback_value: Any = None  # Value to return on timeout/error
    required: bool = False  # If True, stop execution if this chain fails


class ChainOrchestrator:
    """
    Orchestrates parallel/sequential LLM chain execution with timeout handling.

    Manages concurrent execution of multiple LangChain runnables with:
    - Configurable timeouts per chain
    - Fallback values on timeout/error
    - Detailed logging of execution status
    - Both parallel and sequential execution modes
    """

    def __init__(self, default_timeout: float = 30.0):
        """
        Initialize orchestrator.

        Parameters:
            default_timeout: Default timeout in seconds for chains
        """
        self.default_timeout = default_timeout

    def execute_parallel(
        self,
        chains: List[Tuple[ChainExecutionConfig, Runnable, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Execute multiple chains in parallel.

        Parameters:
            chains: List of tuples (config, chain, input_dict)
                - config: ChainExecutionConfig
                - chain: Runnable chain to execute
                - input_dict: Input parameters for chain

        Returns:
            Dict mapping config.name to result (or fallback_value on error)
        """
        results = {}

        with ThreadPoolExecutor(max_workers=len(chains)) as executor:
            futures = {}

            for config, chain, inputs in chains:
                future = executor.submit(chain.invoke, inputs)
                futures[config.name] = (future, config)

            # Process completed futures as they finish
            for future in as_completed(f[0] for f in futures.values()):
                # Find which config this future belongs to
                config_name = None
                config = None
                for name, (fut, cfg) in futures.items():
                    if fut == future:
                        config_name = name
                        config = cfg
                        break

                if config_name is None or config is None:
                    continue

                try:
                    result = future.result(timeout=config.timeout)
                    results[config_name] = result
                    print(f"[ORCHESTRATOR] {config_name}: ✓ Success")
                except TimeoutError:
                    results[config_name] = config.fallback_value
                    print(f"[ORCHESTRATOR] {config_name}: ⏱ Timeout ({config.timeout}s) → fallback")
                except Exception as e:
                    results[config_name] = config.fallback_value
                    print(f"[ORCHESTRATOR] {config_name}: ✗ Error - {type(e).__name__}: {e} → fallback")

        return results

    def execute_sequential(
        self,
        chains: List[Tuple[ChainExecutionConfig, Runnable, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Execute chains sequentially in order.

        Parameters:
            chains: List of tuples (config, chain, input_dict)

        Returns:
            Dict mapping config.name to result (or fallback_value on error)
        """
        results = {}

        for config, chain, inputs in chains:
            try:
                result = chain.invoke(inputs)
                results[config.name] = result
                print(f"[ORCHESTRATOR] {config.name}: ✓ Success")
            except TimeoutError:
                results[config.name] = config.fallback_value
                print(f"[ORCHESTRATOR] {config.name}: ⏱ Timeout ({config.timeout}s) → fallback")
                if config.required:
                    raise
            except Exception as e:
                results[config.name] = config.fallback_value
                print(f"[ORCHESTRATOR] {config.name}: ✗ Error - {type(e).__name__}: {e} → fallback")
                if config.required:
                    raise

        return results
