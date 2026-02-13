"""
Node: Run news-sentiment and chart-technical analysis, then produce a
      trading decision (buy / sell / hold).
"""

from typing import Any, Dict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from graph.state import GraphState
from graph.chains.news_analyzer import news_sentiment_chain
from graph.chains.chart_analyzer import chart_analysis_chain
from graph.chains.trading_decision import trading_decision_chain, TradingDecision


def analyze(state: GraphState) -> Dict[str, Any]:
    print("---ANALYZE---")
    ticker = state["ticker"]
    news_docs = state["news_documents"]
    chart_docs = state["chart_documents"]
    portfolio_context = state.get("portfolio_context", "No portfolio data available.")
    actions_today = state["actions_today"]
    max_actions = state["max_actions"]
    
    # Timeout in seconds for each LLM call
    LLM_TIMEOUT = 30

    try:
        # ── 1. Summarise news sentiment ──────────────────────────────────────
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    news_sentiment_chain.invoke,
                    {
                        "ticker": ticker,
                        "news_documents": "\n\n---\n\n".join(news_docs) if news_docs else "No recent news available.",
                    }
                )
                news_summary = future.result(timeout=LLM_TIMEOUT)
            print(f"[ANALYZE] News summary generated")
        except FuturesTimeoutError:
            print(f"[ANALYZE] ⚠️  News sentiment analysis timed out (>{LLM_TIMEOUT}s)")
            news_summary = "Unable to retrieve news sentiment (timeout). Proceeding with neutral assumption."
        except Exception as e:
            print(f"[ANALYZE] ⚠️  News sentiment analysis failed: {e}")
            news_summary = "Unable to retrieve news sentiment (error). Proceeding with neutral assumption."

        # ── 2. Summarise chart technicals ────────────────────────────────────
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    chart_analysis_chain.invoke,
                    {
                        "ticker": ticker,
                        "chart_documents": "\n\n---\n\n".join(chart_docs) if chart_docs else "No chart data available.",
                    }
                )
                chart_summary = future.result(timeout=LLM_TIMEOUT)
            print(f"[ANALYZE] Chart summary generated")
        except FuturesTimeoutError:
            print(f"[ANALYZE] ⚠️  Chart analysis timed out (>{LLM_TIMEOUT}s)")
            chart_summary = "Unable to retrieve chart analysis (timeout). Proceeding with neutral assumption."
        except Exception as e:
            print(f"[ANALYZE] ⚠️  Chart analysis failed: {e}")
            chart_summary = "Unable to retrieve chart analysis (error). Proceeding with neutral assumption."

        # ── 3. Make trading decision ─────────────────────────────────────────
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    trading_decision_chain.invoke,
                    {
                        "ticker": ticker,
                        "news_summary": news_summary,
                        "chart_summary": chart_summary,
                        "portfolio_context": portfolio_context,
                        "actions_today": actions_today,
                        "max_actions": max_actions,
                    }
                )
                result: TradingDecision = future.result(timeout=LLM_TIMEOUT)  # type: ignore[assignment]
            print(f"[ANALYZE] Decision: {result.decision} (confidence: {result.confidence:.2f})")
        except FuturesTimeoutError:
            print(f"[ANALYZE] ⚠️  Trading decision timed out (>{LLM_TIMEOUT}s), defaulting to HOLD")
            result = TradingDecision(
                decision="hold",
                reasoning="Unable to reach decision due to timeout. Defaulting to HOLD.",
                quantity=0,
                confidence=0.3
            )
        except Exception as e:
            print(f"[ANALYZE] ⚠️  Trading decision failed: {e}, defaulting to HOLD")
            result = TradingDecision(
                decision="hold",
                reasoning="Unable to reach decision due to error. Defaulting to HOLD.",
                quantity=0,
                confidence=0.3
            )

        return {
            "news_summary": news_summary,
            "chart_summary": chart_summary,
            "decision": result.decision,
            "quantity": result.quantity,
            "reasoning": result.reasoning,
        }
    except Exception as e:
        print(f"[ANALYZE] ❌ Unexpected error in analyze node: {e}")
        # Return safe defaults
        return {
            "news_summary": "Error in analysis",
            "chart_summary": "Error in analysis",
            "decision": "hold",
            "quantity": 0,
            "reasoning": "Analysis failed, defaulting to HOLD",
        }
