import plotly.graph_objects as go
import pandas as pd

def render_gauge_chart(value, title):
    """
    Renders an institutional neon-styled AI confidence gauge.
    """
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'color': 'white', 'size': 14}},
        gauge = {
            'axis': {'range': [None, 100], 'tickcolor': "white"},
            'bar': {'color': "#00E676" if value >= 50 else "#FF3D00", 'thickness': 0.75},
            'bgcolor': "#1E1E2E",
            'borderwidth': 2,
            'bordercolor': "#333",
            'steps': [
                {'range': [0, 40], 'color': "rgba(255, 61, 0, 0.2)"},    # Bearish Red
                {'range': [40, 60], 'color': "rgba(255, 193, 7, 0.2)"},  # Neutral Yellow
                {'range': [60, 100], 'color': "rgba(0, 230, 118, 0.2)"}  # Bullish Green
            ],
        }
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={'color': 'white'},
        margin=dict(l=20, r=20, t=40, b=20),
        height=220
    )
    return fig


def render_oi_heatmap(df):
    """
    Phase 11: Institutional Liquidity Heatmap
    Bidirectional Horizontal Bar Chart for Call vs Put OI (Support vs Resistance)
    """
    if df.empty or 'Strike' not in df.columns:
        return go.Figure()
        
    fig = go.Figure()
    
    # 🔴 Call OI (Resistance) - Plotted on negative X-axis to point left
    fig.add_trace(go.Bar(
        y=df['Strike'],
        x=-df['CE_OI'],
        name='Call OI (Resistance)',
        orientation='h',
        marker=dict(
            color='rgba(255, 61, 0, 0.8)',
            line=dict(color='rgba(255, 61, 0, 1.0)', width=1)
        ),
        hoverinfo='y+text',
        hovertext=[f"Strike: {y}<br>Call OI: {x:,.0f}" for x, y in zip(df['CE_OI'], df['Strike'])]
    ))
    
    # 🟢 Put OI (Support) - Plotted on positive X-axis to point right
    fig.add_trace(go.Bar(
        y=df['Strike'],
        x=df['PE_OI'],
        name='Put OI (Support)',
        orientation='h',
        marker=dict(
            color='rgba(0, 230, 118, 0.8)',
            line=dict(color='rgba(0, 230, 118, 1.0)', width=1)
        ),
        hoverinfo='y+text',
        hovertext=[f"Strike: {y}<br>Put OI: {x:,.0f}" for x, y in zip(df['PE_OI'], df['Strike'])]
    ))
    
    # Identify Max CE and PE strikes for highlighting
    max_ce_strike = df.loc[df['CE_OI'].idxmax(), 'Strike'] if not df.empty and df['CE_OI'].sum() > 0 else None
    max_pe_strike = df.loc[df['PE_OI'].idxmax(), 'Strike'] if not df.empty and df['PE_OI'].sum() > 0 else None
    
    fig.update_layout(
        title=dict(
            text="Institutional Liquidity Profile (Support vs Resistance)",
            font=dict(size=16, color="#FFF")
        ),
        barmode='relative',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color='#AAA'),
        yaxis=dict(
            title="Strike Price",
            tickformat="d",
            dtick=50,  # Ensure every 50-point strike is visible
            gridcolor="#333",
            zeroline=False
        ),
        xaxis=dict(
            title="← Resistance (Calls)  |  Support (Puts) →",
            showticklabels=False,
            gridcolor="#222",
            zerolinecolor="#555",
            zerolinewidth=2
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1,
            font=dict(color="white")
        ),
        height=450
    )
    
    # Add highlight lines for the massive walls
    if max_ce_strike:
        fig.add_hline(y=max_ce_strike, line_dash="dot", line_color="rgba(255, 61, 0, 0.5)", annotation_text="Max Call Wall", annotation_position="top left")
    if max_pe_strike:
        fig.add_hline(y=max_pe_strike, line_dash="dot", line_color="rgba(0, 230, 118, 0.5)", annotation_text="Max Put Wall", annotation_position="top right")

    return fig
