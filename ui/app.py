import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from data.dhan_client import DhanMarketData
from analytics.signals import analyze_market
from analytics.institutional import calculate_exposures
from analytics.smart_money import analyze_smart_money
from ui.components import render_gauge_chart, render_oi_heatmap
from core.database import init_db

# --- FALLBACK IMPORTS ---
try:
    from analytics.engine import calculate_advanced_pcr, calculate_max_pain
except ImportError:
    from analytics.engine import calculate_pcr, calculate_max_pain
    def calculate_advanced_pcr(df, ltp):
        val = calculate_pcr(df)
        return val, val

st.set_page_config(page_title="Institutional Quant Engine", layout="wide", page_icon="🏛️")

if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

@st.cache_resource
def get_dhan_client_v11():
    return DhanMarketData()

client = get_dhan_client_v11()

# --- SIDEBAR CONTROLS ---
st.sidebar.title("⚙️ Engine Controls")
ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
today_ist = ist_now.date()
next_tuesday = today_ist + timedelta((1 - today_ist.weekday()) % 7)

expiry_input = st.sidebar.text_input("Target Expiry Date (YYYY-MM-DD)", value=next_tuesday.strftime("%Y-%m-%d"))
live_feed = st.sidebar.toggle("🔴 Auto-Refresh Feed", value=True)
refresh_rate = st.sidebar.slider("Refresh Speed (Seconds)", min_value=3, max_value=60, value=5)

if st.sidebar.button("🔄 Reset Baseline Memory"):
    if 'baseline' in st.session_state:
        del st.session_state['baseline']
    st.sidebar.success("Memory Reset!")

# --- CORE ENGINE LOOP ---
ltp, raw_response = client.get_live_option_chain(expiry_date=expiry_input)
if ltp is None or not raw_response:
    st.error(f"Waiting for Data... Market closed or {expiry_input} not available.")
    st.stop()
    
df = client.process_oc_to_dataframe(raw_response)
if df.empty or "Strike" not in df.columns:
    st.error("Engine failed to parse option chain.")
    st.stop()

if ltp == 0:
    atm_idx = (df['CE_LTP'] - df['PE_LTP']).abs().idxmin()
    ltp = df.loc[atm_idx, 'Strike']

df_filtered = df[(df['Strike'] >= ltp - 600) & (df['Strike'] <= ltp + 600)].copy()

# --- RUN INSTITUTIONAL ENGINES ---
overall_pcr, atm_pcr = calculate_advanced_pcr(df_filtered, ltp)
max_pain = calculate_max_pain(df_filtered)
exposures = calculate_exposures(df_filtered, ltp)
analysis = analyze_market(ltp, df_filtered, max_pain, overall_pcr, atm_pcr)

# --- STATE MEMORY (BASELINE TRACKING) ---
current_total_oi = df_filtered['CE_OI'].sum() + df_filtered['PE_OI'].sum()

if 'baseline' not in st.session_state:
    # Set the baseline on first load
    st.session_state.baseline = {
        'ltp': ltp, 'oi': current_total_oi, 'pcr': overall_pcr, 'time': time.time()
    }
    
# Run Phase 4 & 5 Engines
smart_money = analyze_smart_money(
    current_price=ltp, prev_price=st.session_state.baseline['ltp'],
    current_oi=current_total_oi, prev_oi=st.session_state.baseline['oi'],
    current_pcr=overall_pcr, prev_pcr=st.session_state.baseline['pcr']
)

# ==========================================
# VERSION 2 UI: TOP RIBBON
# ==========================================
st.markdown("""
<style>
    .ribbon-metric { background-color: #1E1E2E; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #333; }
    .ribbon-title { font-size: 0.85em; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .ribbon-val { font-size: 1.4em; font-weight: bold; color: #FFF; }
    .pos-gex { color: #00E676; }
    .neg-gex { color: #FF3D00; }
    .sm-card { padding: 15px; border-radius: 10px; background-color: #1E1E2E; border: 1px solid #333; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ Institutional Decision Intelligence")
st.caption(f"IST: {ist_now.strftime('%H:%M:%S')} | Target Expiry: {expiry_input}")

r1, r2, r3, r4, r5, r6, r7 = st.columns(7)
with r1: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Spot</div><div class='ribbon-val'>₹{ltp:,.0f}</div></div>", unsafe_allow_html=True)
with r2: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>PCR</div><div class='ribbon-val'>{overall_pcr:.2f}</div></div>", unsafe_allow_html=True)
with r3: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Max Pain</div><div class='ribbon-val'>₹{max_pain:,.0f}</div></div>", unsafe_allow_html=True)
with r4: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Net GEX</div><div class='ribbon-val {'pos-gex' if exposures['net_gex'] > 0 else 'neg-gex'}'>{exposures['net_gex']/1e7:,.1f} Cr</div></div>", unsafe_allow_html=True)
with r5: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Gamma Flip</div><div class='ribbon-val'>₹{exposures['gamma_flip']:,.0f}</div></div>", unsafe_allow_html=True)
with r6: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Dealer Regime</div><div class='ribbon-val' style='font-size:1.1em;'>{'Long Gamma' if exposures['net_gex'] > 0 else 'Short Gamma'}</div></div>", unsafe_allow_html=True)
with r7: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Hedging</div><div class='ribbon-val' style='font-size:1.1em;'>{'Bullish' if exposures['net_dex'] < 0 else 'Bearish'}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# MIDDLE ROW 1: SMART MONEY & DIVERGENCE
# ==========================================
sm1, sm2, sm3, sm4 = st.columns(4)
with sm1:
    st.markdown(f"""
    <div class='sm-card'>
        <div style='color: #888; font-size: 0.9em;'>SMART MONEY FLOW</div>
        <div style='color: {smart_money["flow_color"]}; font-size: 1.6em; font-weight: bold;'>{smart_money["flow"]}</div>
        <div style='color: #AAA; font-size: 0.85em;'>Confidence: {smart_money["flow_score"]}%</div>
    </div>
    """, unsafe_allow_html=True)
with sm2:
    st.markdown(f"""
    <div class='sm-card'>
        <div style='color: #888; font-size: 0.9em;'>DIVERGENCE DETECTOR</div>
        <div style='color: {smart_money["div_color"]}; font-size: 1.3em; font-weight: bold; padding-top: 5px;'>{smart_money["divergence"]}</div>
        <div style='color: #AAA; font-size: 0.85em;'>Confidence: {smart_money["div_score"]}%</div>
    </div>
    """, unsafe_allow_html=True)
with sm3: st.plotly_chart(render_gauge_chart(analysis['confluence'], "Overall AI Score"), use_container_width=True)
with sm4: st.plotly_chart(render_gauge_chart(analysis['confidence'], "Win Probability"), use_container_width=True)

# ==========================================
# MIDDLE ROW 2: AI DECISION ENGINE
# ==========================================
color = "#00E676" if "CE" in analysis['recommendation'] else ("#FF3D00" if "PE" in analysis['recommendation'] else "#FFC107")
st.markdown(f"""
<div style="padding: 20px; border-radius: 10px; background-color: #1E1E2E; border-left: 5px solid {color}; margin-top: 10px;">
    <h3 style="margin-top: 0; color: {color};">Trade Setup: {analysis['recommendation']}</h3>
    <p style="color: #AAA;"><b>Market Regime:</b> {analysis['regime']} | <b>Risk Profile:</b> {analysis['risk']}</p>
    <p style="color: #AAA;"><b>Dealer Positioning:</b> {exposures['dealer_regime']} | <b>Smart Money:</b> {smart_money['flow']}</p>
    <hr style="border-color: #333;">
    <div style="font-size: 0.95em; line-height: 1.6;">{analysis['reason']}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# BOTTOM ROW: HEATMAP & GREEKS
# ==========================================
c_chart, c_table = st.columns([2, 2])
with c_chart: 
    st.plotly_chart(render_oi_heatmap(df_filtered), use_container_width=True)
with c_table:
    st.markdown("### Institutional Greeks & Volume")
    atm_df = df_filtered.iloc[(df_filtered['Strike'] - ltp).abs().argsort()[:7]].sort_values('Strike')
    st.dataframe(atm_df[['Strike', 'CE_LTP', 'CE_Volume', 'CE_Gamma', 'PE_Gamma', 'PE_Volume', 'PE_LTP']], hide_index=True, use_container_width=True)

if live_feed:
    time.sleep(refresh_rate)
    st.rerun()
