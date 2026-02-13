"""
Chart and plotting utilities for the dashboard.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create an interactive candlestick chart with volume."""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker} Price", "Volume"),
        row_heights=[0.7, 0.3],
    )
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
        ),
        row=1,
        col=1,
    )
    
    # Volume bars
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker_color="lightblue",
            opacity=0.7,
        ),
        row=2,
        col=1,
    )
    
    # Layout styling
    fig.update_layout(
        title=f"{ticker} Stock Chart",
        xaxis_title="Time",
        yaxis_title="Price ($)",
        template="plotly_dark",
        height=600,
        showlegend=False,
        xaxis_rangeslider_visible=False,
    )
    
    fig.update_xaxes(type="date")
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig


def create_mini_price_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create a small price chart for dashboard tiles."""
    if df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Simple line chart
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"],
        mode='lines',
        line=dict(color='#00cc96', width=2),
        name='Price',
        hovertemplate='%{x}<br>$%{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        height=140,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        xaxis_rangeslider_visible=False,
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig