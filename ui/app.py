import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time
from datetime import datetime, timedelta
from data.dhan_client import DhanMarketData
from analytics.signals import analyze_market
from ui.components import render_gauge_chart, render_oi_heatmap
from core.database import init_db, save_signal

# --- BULLETPROOF IMPORT BLOCK ---
try:
    from analytics.engine import calculate_advanced_pcr, calculate_max_pain
except ImportError:
    from analytics.engine import calculate_pcr, calculate_max_pain
    def calculate_advanced_pcr(df, ltp):
        val = calculate_pcr(df)
        return val, val
# ---------------------------------

st.set_page_config(page_title="Pro NIFTY Options Dash", layout="wide", page_icon="📈")

if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

@st.cache_resource
def get_dhan_client_v8():
    return DhanMarketData()

client = get_dhan_client_v8()

# --- PROFESSIONAL UI SIDEBAR (IST AWARE) ---
st.sidebar.title("⚙️ Engine Controls")
st.sidebar.markdown("---")

# Force calculation based on Indian Standard Time (IST = UTC + 5:30)
ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
today_ist = ist_now.date()

# Auto-calculate next upcoming Tuesday based on IST date
next_tuesday = today_ist + timedelta((1 - today_ist.weekday()) % 7)
expiry_input = st.sidebar.text_input("Target Expiry Date (YYYY-MM-DD)", value=next_tuesday.strftime("%Y-%m-%d"))

st.sidebar.markdown("---")
live_feed = st.sidebar.toggle("🔴 Auto-Refresh Feed", value=True)
refresh_rate = st.sidebar.slider("Refresh Speed (Seconds)", min_value=3, max_value=60, value=5)

if live_feed:
    st.sidebar.success(f"Live feed ON ({refresh_rate}s delays)")
else:
    st.sidebar.warning("Live feed PAUSED")

# --- DASHBOARD UI ---
st.title("⚡ Quantitative Options Engine")
st.caption(f"Server Time (IST): {ist_now.strftime('%Y-%m-%d %H:%M:%S')} | Target Expiry: {expiry_input}")

placeholder = st.empty()

with placeholder.container():
    ltp, oc_raw = client.get_live_option_chain(expiry_date=expiry_input)
    
    if ltp is None or not oc_raw:
        st.error(f"Waiting for Data... Market closed or {expiry_input} not available.")
        st.stop()
        
    df = client.process_oc_to_dataframe(oc_raw)
    
    if df.empty:
        st.error("No option chain data available or structure mismatch.")
        st.stop()
        
    if ltp == 0:
        atm_idx = (df['CE_LTP'] - df['PE_LTP']).abs().idxmin()
        ltp = df.loc[atm_idx, 'Strike']
        
    df_filtered = df[(df['Strike'] >= ltp - 500) & (df['Strike'] <= ltp + 500)]
    
    overall_pcr, atm_pcr = calculate_advanced_pcr(df_filtered, ltp)
    max_pain = calculate_max_pain(df_filtered)
    
    analysis = analyze_market(ltp, df_filtered, max_pain, overall_pcr, atm_pcr)
    
    save_signal({
        "ltp": ltp, "pcr": overall_pcr, "max_pain": max_pain,
        "regime": analysis['regime'],
        "confluence_score": analysis['confluence'],
        "recommendation": analysis['recommendation']
    })

    # TOP CARDS
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("NIFTY Spot", f"₹{ltp:,.2f}")
    c2.metric("Overall PCR", f"{overall_pcr}", delta="Bullish" if overall_pcr > 1 else "Bearish")
    c3.metric("ATM PCR (5-Strike)", f"{atm_pcr}", delta="Momentum Bullish" if atm_pcr > overall_pcr else "Momentum Bearish")
    c4.metric("Max Pain", f"₹{max_pain:,.0f}")
    c5.metric("Market Regime", analysis['regime'])

    st.markdown("---")
    
    c_g1, c_g2, c_sig = st.columns([1,1,2])
    with c_g1: st.plotly_chart(render_gauge_chart(analysis['confluence'], "Confluence Score"), use_container_width=True)
    with c_g2: st.plotly_chart(render_gauge_chart(analysis['confidence'], "Conviction %"), use_container_width=True)
    with c_sig:
        color = "#00E676" if "CE" in analysis['recommendation'] else ("#FF3D00" if "PE" in analysis['recommendation'] else "#FFC107")
        st.markdown(f"""
        <div style="padding: 15px; border-radius: 10px; background-color: #1E2130; border-left: 5px solid {color}; height: 100%;">
            <h3 style="margin-top: 0; color: {color};">{analysis['recommendation']}</h3>
            <p style="margin-bottom: 5px; color: gray;"><b>Risk Profile:</b> {analysis['risk']}</p>
            <div style="font-size: 0.95em; line-height: 1.6;">
                {analysis['reason']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    c_chart, c_table = st.columns([2, 2])
    with c_chart: st.plotly_chart(render_oi_heatmap(df_filtered), use_container_width=True)
    with c_table:
        st.markdown("### Live Greeks & IV (ATM)")
        atm_df = df_filtered.iloc[(df_filtered['Strike'] - ltp).abs().argsort()[:5]].sort_values('Strike')
        st.dataframe(atm_df[['Strike', 'CE_LTP', 'CE_Delta', 'CE_IV', 'PE_LTP', 'PE_Delta', 'PE_IV']], hide_index=True, use_container_width=True)

if live_feed:
    time.sleep(refresh_rate)
    st.rerun()
