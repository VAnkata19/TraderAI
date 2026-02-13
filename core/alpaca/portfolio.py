"""Portfolio context building for LLM consumption."""

from typing import List

from .account import get_account, get_position, get_positions
from .market_data import get_current_price


def build_portfolio_context(ticker: str) -> str:
    """
    Build a human-readable summary of the Alpaca account, current position
    in *ticker*, and its live price – ready to inject into the LLM prompt.
    """
    lines: List[str] = []

    try:
        acct = get_account()
        lines.append(
            f"Account equity: ${float(acct['equity']):,.2f}  |  "
            f"Buying power: ${float(acct['buying_power']):,.2f}  |  "
            f"Cash: ${float(acct['cash']):,.2f}"
        )
    except Exception as e:
        lines.append(f"Account info unavailable: {e}")

    try:
        price = get_current_price(ticker)
        lines.append(f"Current price of {ticker}: ${price:,.2f}")
    except Exception as e:
        lines.append(f"Current price unavailable: {e}")

    try:
        pos = get_position(ticker)
        if pos:
            qty = float(pos["qty"])
            avg_entry = float(pos["avg_entry_price"])
            market_value = float(pos["market_value"])
            unrealised_pl = float(pos["unrealized_pl"])
            unrealised_pct = float(pos["unrealized_plpc"]) * 100
            lines.append(
                f"Current position in {ticker}: {qty:.0f} shares @ avg ${avg_entry:,.2f}  |  "
                f"Market value: ${market_value:,.2f}  |  "
                f"Unrealised P/L: ${unrealised_pl:,.2f} ({unrealised_pct:+.2f}%)"
            )
        else:
            lines.append(f"No open position in {ticker}.")
    except Exception as e:
        lines.append(f"Position info unavailable: {e}")

    # Also list all positions briefly
    try:
        all_positions = get_positions()
        if all_positions:
            pos_strs = []
            for p in all_positions:
                sym = p["symbol"]
                q = float(p["qty"])
                upl = float(p["unrealized_pl"])
                pos_strs.append(f"{sym}: {q:.0f} shares (P/L ${upl:,.2f})")
            lines.append(f"All positions: {' | '.join(pos_strs)}")
        else:
            lines.append("Portfolio is empty – no open positions.")
    except Exception as e:
        lines.append(f"Positions list unavailable: {e}")

    return "\n".join(lines)
