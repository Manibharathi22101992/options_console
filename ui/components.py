import plotly.graph_objects as go

def render_gauge_chart(score, title):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        title = {'text': title, 'font': {'color': "white"}},
        gauge = {
            'axis': {'range': [None, 100], 'tickcolor': "white"},
            'bar': {'color': "#00E676" if score > 50 else "#FF3D00"},
            'steps': [
                {'range': [0, 30], 'color': "#3b1c1f"},
                {'range': [30, 70], 'color': "#1e2130"},
                {'range': [70, 100], 'color': "#163823"}],
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=250, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def render_oi_heatmap(df):
    fig = go.Figure(data=[
        go.Bar(name='CE OI', x=df['Strike'], y=df['CE_OI'], marker_color='#FF3D00'),
        go.Bar(name='PE OI', x=df['Strike'], y=df['PE_OI'], marker_color='#00E676')
    ])
    fig.update_layout(
        barmode='group',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={'color': "white"},
        title="Open Interest Profile",
        xaxis_title="Strike Price",
        yaxis_title="Open Interest"
    )
    return fig
