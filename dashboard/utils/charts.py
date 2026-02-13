"""
Chart and plotting utilities for the dashboard.
"""

from typing import Optional
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone, time
import pytz


def is_market_hours(timestamp: pd.Timestamp) -> bool:
    """
    Check if timestamp is during regular US market hours (9:30 AM - 4:00 PM EST).
    """
    # Convert to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    if timestamp.tz is None:
        # Assume UTC if no timezone
        timestamp = timestamp.tz_localize(pytz.UTC)
    
    eastern_time = timestamp.astimezone(eastern)
    
    # Check if weekday (Monday=0, Sunday=6)
    if eastern_time.weekday() >= 5:  # Weekend
        return False
    
    # Market hours: 9:30 AM to 4:00 PM EST
    market_open = time(9, 30)
    market_close = time(16, 0)
    
    return market_open <= eastern_time.time() <= market_close


def convert_to_display_time(df: pd.DataFrame, target_timezone: Optional[str] = None) -> pd.DataFrame:
    """
    Convert DataFrame timestamps from Eastern time to target timezone for display.
    Market data comes in Eastern time, but we want to display in user's selected time.
    """
    if df.empty:
        return df
    
    # Get target timezone - fallback to auto-detect if not specified
    if target_timezone:
        try:
            display_tz = pytz.timezone(target_timezone)
        except:
            # Fallback to local timezone if invalid timezone string
            display_tz = datetime.now().astimezone().tzinfo
    else:
        # Auto-detect local timezone as fallback
        display_tz = datetime.now().astimezone().tzinfo
    
    eastern = pytz.timezone('US/Eastern')
    
    # Convert index from Eastern to display time
    df_display = df.copy()
    
    # Ensure index is DatetimeIndex
    if not isinstance(df_display.index, pd.DatetimeIndex):
        df_display.index = pd.to_datetime(df_display.index)
    
    if df_display.index.tz is None:
        # Assume Eastern time if no timezone info
        df_display.index = df_display.index.tz_localize(eastern)
    
    # Convert to display timezone
    df_display.index = df_display.index.tz_convert(display_tz)
    
    return df_display


def split_market_hours_data(df: pd.DataFrame, display_timezone: Optional[str] = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split dataframe into market hours and non-market hours data.
    Returns (market_hours_df, off_hours_df)
    Note: Market hours detection stays in Eastern time, but data is converted to display timezone.
    """
    if df.empty:
        return df, df
    
    # Create boolean mask for market hours (using original Eastern time)
    if isinstance(df.index, pd.DatetimeIndex):
        market_mask = df.index.to_series().map(is_market_hours)
    else:
        market_mask = pd.Series([False] * len(df), index=df.index)
    
    market_hours_df = df[market_mask]
    off_hours_df = df[~market_mask]
    
    # Convert both to display timezone
    market_hours_display = convert_to_display_time(market_hours_df, display_timezone)
    off_hours_display = convert_to_display_time(off_hours_df, display_timezone)
    
    return market_hours_display, off_hours_display


def create_candlestick_chart(df: pd.DataFrame, ticker: str, display_timezone: Optional[str] = None) -> go.Figure:
    """Create an interactive candlestick chart with volume and market hours styling."""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker} Price", "Volume"),
        row_heights=[0.7, 0.3],
    )
    
    # Split data by market hours with display timezone
    market_df, off_hours_df = split_market_hours_data(df, display_timezone)
    
    # Add off-hours candlesticks (grey)
    if not off_hours_df.empty:
        fig.add_trace(
            go.Candlestick(
                x=off_hours_df.index,
                open=off_hours_df["Open"],
                high=off_hours_df["High"],
                low=off_hours_df["Low"],
                close=off_hours_df["Close"],
                name="Pre/Post Market",
                increasing_line_color="#666666",
                decreasing_line_color="#444444",
                increasing_fillcolor="#666666",
                decreasing_fillcolor="#444444",
                opacity=0.6,
            ),
            row=1,
            col=1,
        )
    
    # Add market hours candlesticks (colored)
    if not market_df.empty:
        fig.add_trace(
            go.Candlestick(
                x=market_df.index,
                open=market_df["Open"],
                high=market_df["High"],
                low=market_df["Low"],
                close=market_df["Close"],
                name="Market Hours",
                increasing_line_color="#2ecc71",
                decreasing_line_color="#e74c3c",
                increasing_fillcolor="#2ecc71",
                decreasing_fillcolor="#e74c3c",
            ),
            row=1,
            col=1,
        )
    
    # Add volume bars with market hours styling
    if not off_hours_df.empty:
        fig.add_trace(
            go.Bar(
                x=off_hours_df.index,
                y=off_hours_df["Volume"],
                name="Pre/Post Volume",
                marker_color="#666666",
                opacity=0.4,
            ),
            row=2,
            col=1,
        )
    
    if not market_df.empty:
        bar_colors = [
            "#2ecc71" if row["Close"] >= row["Open"] else "#e74c3c"
            for _, row in market_df.iterrows()
        ]
        fig.add_trace(
            go.Bar(
                x=market_df.index,
                y=market_df["Volume"],
                name="Market Volume",
                marker_color=bar_colors,
                opacity=0.7,
            ),
            row=2,
            col=1,
        )
    
    # Layout styling
    timezone_display = f"Time ({display_timezone})" if display_timezone else "Time (Local)"
    fig.update_layout(
        title=f"{ticker} Stock Chart",
        xaxis_title=timezone_display,
        yaxis_title="Price ($)",
        template="plotly_dark",
        height=600,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    fig.update_xaxes(type="date")
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig
    
    fig.update_xaxes(type="date")
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig


def create_mini_price_chart(df: pd.DataFrame, ticker: str, display_timezone: Optional[str] = None) -> go.Figure:
    """Create a small price chart for dashboard tiles with market hours styling."""
    if df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Split data by market hours with display timezone
    market_df, off_hours_df = split_market_hours_data(df, display_timezone)
    
    # Add off-hours line (grey)
    if not off_hours_df.empty:
        fig.add_trace(go.Scatter(
            x=off_hours_df.index,
            y=off_hours_df["Close"],
            mode='lines',
            line=dict(color='#888888', width=2),
            name='Pre/Post Market',
            hovertemplate='%{x}<br>$%{y:.2f}<extra></extra>',
            opacity=0.6
        ))
    
    # Add market hours line (colored)
    if not market_df.empty:
        # Determine overall trend color
        if len(market_df) > 0:
            start_price = market_df["Close"].iloc[0]
            end_price = market_df["Close"].iloc[-1]
            trend_color = '#2ecc71' if end_price >= start_price else '#e74c3c'
        else:
            trend_color = '#00cc96'
        
        fig.add_trace(go.Scatter(
            x=market_df.index,
            y=market_df["Close"],
            mode='lines',
            line=dict(color=trend_color, width=2),
            name='Market Hours',
            hovertemplate='%{x}<br>$%{y:.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        height=100,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        xaxis_rangeslider_visible=False,
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig