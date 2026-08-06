import sys
import os

# Tell Python to look in the main folder for our other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time
from data.dhan_client import DhanMarketData
from analytics.engine import calculate_pcr, calculate_max_pain
from analytics.signals import analyze_market
from ui.components import render_gauge_chart, render_oi_heatmap
from core.database import init_db, save_signal

# Configuration
st.set_page_config(page_title="Pro NIFTY Options Dash", layout="wide", page_icon="📈")

# Database Initialization
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# We renamed this function to "get_new_dhan_client" to force Streamlit 
# to clear its memory and use our new v2.x Dhan API login fix!
@st.cache_resource
def get_new_dhan_client():
    return DhanMarketData()

client = get_new_dhan_client()

# --- Live Feed Toggle in Sidebar ---
st.sidebar.title("Controls")
live_feed = st.sidebar.toggle("🔴 Live Market Feed", value=True)
if live_feed:
    st.sidebar.success("Live feed is ON (Updating every 3s)")
else:
    st.sidebar.warning("Live feed is PAUSED")
# ----------------------------------------

st.title("⚡ NIFTY Pro Intraday Options Dashboard")

# Placeholder for auto-refreshing dashboard
placeholder = st.empty()

with placeholder.container():
    ltp, oc_raw = client.get_live_option_chain()
    
    if ltp is None or oc_raw is None:
        st.error("Waiting for Market Data... Ensure Market is open and API credentials in Secrets are correct.")
        st.stop()
        
    df = client.process_oc_to_dataframe(oc_raw)
    
    if df.empty:
        st.warning("No option chain data available for this expiry.")
        st.stop()
        
    # Filter 10 strikes above and below ATM
    df_filtered = df[(df['Strike'] >= ltp - 500) & (df['Strike'] <= ltp + 500)]
    
    pcr = calculate_pcr(df_filtered)
    max_pain = calculate_max_pain(df_filtered)
    analysis = analyze_market(ltp, df_filtered, max_pain)
    
    save_signal({
        "ltp": ltp, "pcr": pcr, "max_pain": max_pain,
        "regime": analysis['regime'],
        "confluence_score": analysis['confluence'],
        "recommendation": analysis['recommendation']
    })

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("NIFTY Spot", f"₹{ltp:,.2f}")
    col2.metric("PCR", f"{pcr}", delta="Bullish" if pcr > 1 else "Bearish", delta_color="normal")
    col3.metric("Max Pain", f"₹{max_pain:,.0f}")
    col4.metric("Market Regime", analysis['regime'])

    st.markdown("---")
    
    c1, c2, c3 = st.columns([1,1,2])
    with c1: st.plotly_chart(render_gauge_chart(analysis['confluence'], "Confluence Score"), use_container_width=True)
    with c2: st.plotly_chart(render_gauge_chart(analysis['confidence'], "Confidence %"), use_container_width=True)
    with c3:
        color = "#00E676" if "CE" in analysis['recommendation'] else ("#FF3D00" if "PE" in analysis['recommendation'] else "#FFC107")
        st.markdown(f"""
        <div style="padding: 20px; border-radius: 10px; background-color: #1E2130; border-left: 5px solid {color}; height: 100%;">
            <h3 style="margin-top: 0; color: {color};">Signal: {analysis['recommendation']}</h3>
            <p style="font-size: 1.1em;"><b>Reasoning:</b> {analysis['reason']}</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    c_chart, c_table = st.columns([2, 2])
    with c_chart: st.plotly_chart(render_oi_heatmap(df_filtered), use_container_width=True)
    with c_table:
        st.markdown("### Live Greeks & IV (ATM)")
        atm_df = df_filtered.iloc[(df_filtered['Strike'] - ltp).abs().argsort()[:5]].sort_values('Strike')
        st.dataframe(atm_df[['Strike', 'CE_LTP', 'CE_Delta', 'CE_IV', 'PE_LTP', 'PE_Delta', 'PE_IV']], hide_index=True, use_container_width=True)

# Only loop if the toggle is ON
if live_feed:
    time.sleep(3)
    st.rerun()
