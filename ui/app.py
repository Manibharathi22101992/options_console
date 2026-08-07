import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from data.dhan_client import DhanMarketData
from analytics.institutional import calculate_exposures
from analytics.smart_money import analyze_smart_money
from analytics.volatility import analyze_volatility
from analytics.market_structure import analyze_market_structure
from analytics.volume_profile import calculate_volume_profile
from analytics.pcr_engine import calculate_nonlinear_pcr_score
from decision.recommendation_engine import generate_institutional_decision
from analytics.alerts import check_smart_alerts, send_telegram_alert
from storage.feature_store import init_feature_store, log_snapshot, compute_features
from ui.components import render_oi_heatmap

try:
    from analytics.engine import calculate_advanced_pcr, calculate_max_pain
except ImportError:
    from analytics.engine import calculate_pcr, calculate_max_pain
    def calculate_advanced_pcr(df, ltp):
        val = calculate_pcr(df)
        return val, val

st.set_page_config(page_title="Institutional Quant Terminal V2.99", layout="wide", page_icon="🏛️")

# Initialize feature store DB
init_feature_store()

@st.cache_resource
def get_client() -> DhanMarketData:
    return DhanMarketData()

client = get_client()

# Sidebar Controls
st.sidebar.title("⚙️ Terminal Engine")
ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
expiry_input = st.sidebar.text_input("Target Expiry Date (YYYY-MM-DD)", value=(ist_now.date() + timedelta((1 - ist_now.date().weekday()) % 7)).strftime("%Y-%m-%d"))
live_feed = st.sidebar.toggle("🔴 Auto-Refresh Feed", value=True)
refresh_rate = st.sidebar.slider("Refresh Speed (Sec)", 3, 60, 5)

if st.sidebar.button("🔄 Reset Baseline Memory"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.sidebar.success("Baselines reset successfully!")

# --- DATA PIPELINE & LATENCY LOGGING ---
api_start = time.time()
ltp, raw_response = client.get_live_option_chain(expiry_date=expiry_input)
api_latency = (time.time() - api_start) * 1000

if ltp is None or not raw_response:
    st.error("Waiting for Market Data Feed...")
    st.stop()

df = client.process_oc_to_dataframe(raw_response)
if ltp == 0:
    ltp = df.loc[(df['CE_LTP'] - df['PE_LTP']).abs().idxmin(), 'Strike']
df_filtered = df[(df['Strike'] >= ltp - 600) & (df['Strike'] <= ltp + 600)].copy()

calc_start = time.time()
overall_pcr, _ = calculate_advanced_pcr(df_filtered, ltp)
max_pain = calculate_max_pain(df_filtered)
exposures = calculate_exposures(df_filtered, ltp)
vp = calculate_volume_profile(df_filtered)

total_oi = float(df_filtered['CE_OI'].sum() + df_filtered['PE_OI'].sum())
total_vol = float(df_filtered['CE_Volume'].sum() + df_filtered['PE_Volume'].sum())

# Multi-Timeframe Baseline Management
if 'baselines' not in st.session_state:
    st.session_state.baselines = {
        "open": ltp,
        "vwap": ltp, # Proxy initializer
        "oi": total_oi,
        "pcr": overall_pcr
    }

# Log snapshot for feature store momentum tracking
vol_analysis = analyze_volatility(df_filtered, ltp, st.session_state.baselines['open'], expiry_input)
log_snapshot(ltp, overall_pcr, total_oi, exposures['net_gex'], exposures['net_dex'], vol_analysis['atm_iv'], total_vol)
features = compute_features()

smart_money = analyze_smart_money(ltp, st.session_state.baselines['open'], features)
pcr_score = calculate_nonlinear_pcr_score(overall_pcr)

# Opening range proxies
orh = ltp + 40
orl = ltp - 40
structure = analyze_market_structure(
    exposures['net_gex'], overall_pcr, smart_money['flow_score'], 
    ltp, st.session_state.baselines['vwap'], orh, orl, max_pain, vol_analysis['expected_move']/4
)

dec = generate_institutional_decision(
    ltp, st.session_state.baselines, pcr_score, 
    exposures['net_gex'], exposures['net_dex'], vol_analysis['expected_move'], smart_money['flow_score']
)
calc_latency = (time.time() - calc_start) * 1000

# ==========================================
# UI STYLING & LAYOUT POLISH
# ==========================================
st.markdown("""
<style>
.rib { background: #161824; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #333; }
.rib-t { font-size: 0.75em; color: #888; text-transform: uppercase; letter-spacing: 1px; }
.rib-v { font-size: 1.25em; font-weight: bold; color: #FFF; }
.card { background: #161824; padding: 20px; border-radius: 10px; border: 1px solid #333; height: 100%; }
.bar-bg { width: 100%; background: #222; border-radius: 5px; height: 14px; margin-top: 6px; }
.bar-fg { height: 100%; border-radius: 5px; }
.target-box { background: #1E1E2E; padding: 12px; border-radius: 6px; text-align: center; flex: 1; margin: 0 4px; border: 1px solid #333; }
.health-footer { background: #0E1117; border-top: 1px solid #333; padding: 8px; text-align: center; font-family: monospace; font-size: 0.85em; color: #888; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ Institutional Quant Terminal V2.99")
st.caption(f"IST: {ist_now.strftime('%H:%M:%S')} | Expiry: {expiry_input}")

# Compact KPI Ribbon
r1, r2, r3, r4, r5, r6 = st.columns(6)
with r1: st.markdown(f"<div class='rib'><div class='rib-t'>Spot</div><div class='rib-v'>₹{ltp:,.0f}</div></div>", unsafe_allow_html=True)
with r2: st.markdown(f"<div class='rib'><div class='rib-t'>VWAP Proxy</div><div class='rib-v'>₹{st.session_state.baselines['vwap']:,.0f}</div></div>", unsafe_allow_html=True)
with r3: st.markdown(f"<div class='rib'><div class='rib-t'>Expected Move</div><div class='rib-v'>±{vol_analysis['expected_move']:.0f}</div></div>", unsafe_allow_html=True)
with r4: st.markdown(f"<div class='rib'><div class='rib-t'>Inst. Score</div><div class='rib-v' style='color:{dec['color']}'>{dec['score']}/100</div></div>", unsafe_allow_html=True)
with r5: st.markdown(f"<div class='rib'><div class='rib-t'>Confidence</div><div class='rib-v'>{dec['confidence']}%</div></div>", unsafe_allow_html=True)
with r6: st.markdown(f"<div class='rib'><div class='rib-t'>Market Regime</div><div class='rib-v' style='color:{structure['color']}; font-size:0.9em;'>{structure['regime']}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Three-Panel Institutional Layout
c_left, c_center, c_right = st.columns([1.2, 2.4, 1.2])

# Left Panel: Market Intelligence Layer
with c_left:
    st.markdown(f"""
<div class='card'>
<div style='color:#888; font-size:0.85em; letter-spacing:1px; margin-bottom:15px;'>MARKET STRUCTURE</div>
<div style='margin-bottom:15px;'>
    <div style='display:flex; justify-content:space-between;'><span>Trend Strength</span><span style='color:#00E676;'>{structure['trend_label']} ({structure['trend_strength']}%)</span></div>
    <div class='bar-bg'><div class='bar-fg' style='width:{structure['trend_strength']}%; background:#00E676;'></div></div>
</div>
<div style='font-size:0.85em; color:#AAA; margin-bottom:15px;'>Status: <b>{structure['or_status']}</b></div>
<hr style='border-color:#333;'>
<div style='color:#888; font-size:0.75em; letter-spacing:1px; margin-bottom:8px;'>VALUE AREA ROTATION</div>
<div style='display:flex; justify-content:space-between; font-size:0.9em;'><span>VAH</span><span style='color:#00E676;'>₹{vp['vah']:.0f}</span></div>
<div style='display:flex; justify-content:space-between; font-size:0.9em;'><span>POC ({vp['poc_shift']})</span><span style='color:#FFF; font-weight:bold;'>₹{vp['poc']:.0f}</span></div>
<div style='display:flex; justify-content:space-between; font-size:0.9em;'><span>VAL</span><span style='color:#FF3D00;'>₹{vp['val']:.0f}</span></div>
<hr style='border-color:#333;'>
<div style='display:flex; justify-content:space-between; font-size:0.9em;'><span>Flow State</span><span style='color:{smart_money["flow_color"]}; font-weight:bold;'>{smart_money["flow"]}</span></div>
</div>
""", unsafe_allow_html=True)

# Center Panel: Decision Panel & Trade Planner (Visual Center)
with c_center:
    contrib_html = "".join([f"<div style='display:flex; justify-content:space-between; font-size:0.85em; padding:3px 0;'><span>{k}</span><span style='color:{'#00E676' if v>0 else '#888'};'>+{v} pts</span></div>" for k, v in dec['contributions'].items()])
    
    st.markdown(f"""
<div class='card' style='border-left: 5px solid {dec['color']};'>
<div style='display:flex; justify-content:space-between; align-items:center;'>
    <div>
        <h1 style='margin:0; color:{dec['color']}; font-size:1.8em;'>{dec['signal']}</h1>
        <span style='color:#888; font-size:0.85em;'>Institutional Execution & Factor Attribution</span>
    </div>
    <div style='text-align:right;'>
        <div style='font-size:2.2em; font-weight:bold; color:#FFF;'>{dec['score']}</div>
        <div style='color:#888; font-size:0.75em;'>INST. SCORE</div>
    </div>
</div>

<div style='margin-top:15px; background:#0E1117; padding:12px; border-radius:8px;'>
    <div style='color:#888; font-size:0.75em; text-transform:uppercase; margin-bottom:6px; letter-spacing:1px;'>Factor Point Contributions</div>
    {contrib_html}
</div>

<div style='display:flex; justify-content:space-between; margin-top:20px;'>
    <div class='target-box'>
        <div style='color:#888; font-size:0.75em;'>ENTRY</div>
        <div style='font-size:1.1em; font-weight:bold;'>₹{dec['entry']:.0f}</div>
    </div>
    <div class='target-box'>
        <div style='color:#888; font-size:0.75em;'>STOP LOSS</div>
        <div style='font-size:1.1em; font-weight:bold; color:#FF3D00;'>₹{dec['sl']:.0f}</div>
    </div>
    <div class='target-box'>
        <div style='color:#888; font-size:0.75em;'>TARGET 1</div>
        <div style='font-size:1.1em; font-weight:bold; color:#00E676;'>₹{dec['t1']:.0f}</div>
    </div>
    <div class='target-box'>
        <div style='color:#888; font-size:0.75em;'>TARGET 2</div>
        <div style='font-size:1.1em; font-weight:bold; color:#00E676;'>₹{dec['t2']:.0f}</div>
    </div>
    <div class='target-box'>
        <div style='color:#888; font-size:0.75em;'>RISK:REWARD</div>
        <div style='font-size:1.1em; font-weight:bold;'>{dec['rr']}</div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

# Right Panel: Probability Distribution Gauges
with c_right:
    st.markdown(f"""
<div class='card'>
<div style='color:#888; font-size:0.85em; letter-spacing:1px; margin-bottom:20px;'>PROBABILITY DISTRIBUTION</div>

<div style='margin-bottom: 15px;'>
    <div style='display:flex; justify-content:space-between; font-size:0.9em;'><span style='color:#00E676; font-weight:bold;'>BULLISH</span><span>{dec["bull_prob"]}%</span></div>
    <div class='bar-bg'><div class='bar-fg' style='width: {dec["bull_prob"]}%; background: #00E676;'></div></div>
</div>

<div style='margin-bottom: 15px;'>
    <div style='display:flex; justify-content:space-between; font-size:0.9em;'><span style='color:#FFC107; font-weight:bold;'>SIDEWAYS</span><span>{dec["side_prob"]}%</span></div>
    <div class='bar-bg'><div class='bar-fg' style='width: {dec["side_prob"]}%; background: #FFC107;'></div></div>
</div>

<div style='margin-bottom: 15px;'>
    <div style='display:flex; justify-content:space-between; font-size:0.9em;'><span style='color:#FF3D00; font-weight:bold;'>BEARISH</span><span>{dec["bear_prob"]}%</span></div>
    <div class='bar-bg'><div class='bar-fg' style='width: {dec["bear_prob"]}%; background: #FF3D00;'></div></div>
</div>
<hr style='border-color:#333;'>
<div style='color:{smart_money["div_color"]}; font-size:0.85em; text-align:center;'><b>{smart_money["divergence"]}</b></div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Bottom Panel: Institutional Heatmap & Order Book Depth
c_chart, c_table = st.columns([2, 2])
with c_chart: 
    st.plotly_chart(render_oi_heatmap(df_filtered), use_container_width=True)
with c_table:
    st.markdown("### Institutional Greeks & Volume")
    atm_df = df_filtered.iloc[(df_filtered['Strike'] - ltp).abs().argsort()[:7]].sort_values('Strike')
    st.dataframe(atm_df[['Strike', 'CE_LTP', 'CE_Volume', 'CE_Gamma', 'PE_Gamma', 'PE_Volume', 'PE_LTP']], hide_index=True, use_container_width=True)

# Smart Alerts Handler
if 'active_alerts' not in st.session_state: 
    st.session_state.active_alerts = []
current_alerts = check_smart_alerts(ltp, st.session_state.baselines['open'], exposures['gamma_flip'], smart_money['flow'], smart_money['divergence'], overall_pcr, st.session_state.baselines['pcr'])
for alert in current_alerts:
    if alert['msg'] not in st.session_state.active_alerts:
        st.toast(alert['msg'], icon=alert['icon'])
        send_telegram_alert(alert['msg'], alert['icon'])
        st.session_state.active_alerts.append(alert['msg'])

# Engineering System Health & Latency Logging Footer
st.markdown(f"""
<div class='health-footer'>
<span>🟢 SYSTEM HEALTH: V2.99 | </span>
<span>Dhan API Latency: <span style='color:#00E676;'>{api_latency:.1f} ms</span> | </span>
<span>Decision Engine Latency: <span style='color:#00E676;'>{calc_latency:.1f} ms</span> | </span>
<span>Feature Store Rolling Buffer: <span style='color:#00E676;'>Active</span></span>
</div>
""", unsafe_allow_html=True)

if live_feed:
    time.sleep(refresh_rate)
    st.rerun()
