"""
Trading analysis loop management.
"""

import threading
import streamlit as st
from datetime import datetime, timezone
from config import RUN_INTERVAL_SECONDS, MAX_ACTIONS_PER_DAY
from dashboard.utils.storage import load_actions_today, save_actions_today


def get_max_actions() -> int:
    """Get max actions from session state or fallback to config."""
    try:
        return st.session_state.get('max_actions_per_day', MAX_ACTIONS_PER_DAY)
    except Exception:
        # Fallback if session state not available (background threads)
        return MAX_ACTIONS_PER_DAY

# Track last run times for each ticker
_last_run_times = {}


def _run_analysis_loop(ticker: str, stop_flag: threading.Event) -> None:
    """Background trading analysis loop for a specific ticker."""
    global _last_run_times
    print(f"[ANALYSIS] Started analysis loop for {ticker}")
    
    while not stop_flag.is_set():
        try:
            # Update last run time
            _last_run_times[ticker] = datetime.now(timezone.utc)
            
            # Check if we've hit the daily action limit
            actions_today = load_actions_today()
            ticker_actions = actions_today.get(ticker, 0)
            max_actions = get_max_actions()
            
            if max_actions != -1 and ticker_actions >= max_actions:
                print(f"[ANALYSIS] {ticker} hit daily limit ({ticker_actions}/{max_actions})")
                stop_flag.wait(300)  # Wait 5 minutes before checking again
                continue
            
            print(f"[ANALYSIS] Running analysis cycle for {ticker}...")
            
            # Import here to avoid circular imports
            from graph.graph import app
            from graph.state import GraphState
            
            # Run the trading graph
            initial_state: GraphState = {
                "ticker": ticker,
                "news_documents": [],
                "chart_documents": [],
                "news_summary": "",
                "chart_summary": "",
                "portfolio_context": "",
                "decision": "",
                "quantity": 0,
                "reasoning": "",
                "actions_today": ticker_actions,
                "max_actions": get_max_actions(),
                "executed": False,
                "order_result": "",
            }
            
            result = app.invoke(initial_state)
            
            if result.get("decision") in ["buy", "sell"]:
                # Update action count
                actions_today[ticker] = actions_today.get(ticker, 0) + 1
                save_actions_today(actions_today)
                print(f"[ANALYSIS] {ticker}: {result['decision'].upper()} - Daily count: {actions_today[ticker]}")
            
            # Wait for next cycle or stop signal
            if not stop_flag.wait(RUN_INTERVAL_SECONDS):
                continue
            else:
                break
                
        except Exception as e:
            print(f"[ANALYSIS] Error in {ticker} loop: {e}")
            # Wait a bit before retrying
            if stop_flag.wait(60):
                break
    
    print(f"[ANALYSIS] Stopped analysis loop for {ticker}")


def start_analysis_loop(ticker: str) -> None:
    """Start the analysis loop for a ticker in a background thread."""
    # Stop existing thread if running
    stop_analysis_loop(ticker)
    
    # Create new stop flag and thread
    stop_flag = threading.Event()
    thread = threading.Thread(
        target=_run_analysis_loop,
        args=(ticker, stop_flag),
        daemon=True,
        name=f"analysis-{ticker}"
    )
    
    # Store references in session state
    st.session_state.stop_flags[ticker] = stop_flag
    st.session_state.analysis_threads[ticker] = thread
    
    # Start the thread
    thread.start()
    print(f"[ANALYSIS] Started background analysis for {ticker}")


def stop_analysis_loop(ticker: str) -> None:
    """Stop the analysis loop for a ticker.""" 
    # Signal the thread to stop
    stop_flag = st.session_state.stop_flags.get(ticker)
    if stop_flag:
        stop_flag.set()
    
    # Wait for thread to finish (with timeout)
    thread = st.session_state.analysis_threads.get(ticker)
    if thread and thread.is_alive():
        thread.join(timeout=2.0)  # Wait max 2 seconds
        if thread.is_alive():
            print(f"[ANALYSIS] Warning: {ticker} thread did not stop cleanly")
    
    # Clean up references
    st.session_state.stop_flags.pop(ticker, None)
    st.session_state.analysis_threads.pop(ticker, None)
    
    print(f"[ANALYSIS] Stopped analysis loop for {ticker}")


def stop_all_analysis_loops() -> None:
    """Stop all running analysis loops."""
    for ticker in list(st.session_state.analysis_threads.keys()):
        stop_analysis_loop(ticker)


def is_analysis_running(ticker: str) -> bool:
    """Check if analysis loop is currently running for a ticker."""
    thread = st.session_state.analysis_threads.get(ticker)
    return thread is not None and thread.is_alive()


def get_time_until_next_run(ticker: str) -> tuple[int, int]:
    """
    Get minutes and seconds until next analysis run for a ticker.
    Returns (minutes, seconds).
    """
    global _last_run_times
    
    if ticker not in _last_run_times:
        # If we haven't started yet, return full interval
        minutes = RUN_INTERVAL_SECONDS // 60
        seconds = RUN_INTERVAL_SECONDS % 60
        return (minutes, seconds)
    
    # Calculate time since last run
    last_run = _last_run_times[ticker]
    now = datetime.now(timezone.utc)
    elapsed = (now - last_run).total_seconds()
    
    # Calculate remaining time
    remaining = max(0, RUN_INTERVAL_SECONDS - elapsed)
    
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    
    return (minutes, seconds)