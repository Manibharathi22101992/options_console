import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from data.dhan_client import DhanMarketData
from analytics.institutional import calculate_exposures
from analytics.smart_money import analyze_smart_money
from analytics.volatility import analyze_volatility
from analytics.market_structure import analyze_market_structure
from analytics.alerts import check_smart_alerts, send_telegram_alert
from analytics.volume_profile import calculate_volume_profile
from decision.recommendation_engine import generate_institutional_decision
from ui.components import render_oi_heatmap
from core.database import init_db

try:
    from analytics.engine import calculate_advanced_pcr, calculate_max_pain
except ImportError:
    from analytics.engine import calculate_pcr, calculate_max_pain
    def calculate_advanced_pcr(df, ltp):
        val = calculate_pcr(df)
        return val, val

st.set_page_config(page_title="Institutional Quant Engine 2.99", layout="wide", page_icon="🏛️")

if 'db_initialized' not in st.session_state:
    init_db()
    # Phase 7 & 8: Historical Intelligence Table
    conn = sqlite3.connect('quant_engine.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (timestamp TEXT, ltp REAL, inst_score INTEGER, confidence INTEGER, regime TEXT, signal TEXT)''')
    conn.commit()
    conn.close()
    st.session_state.db_initialized = True

@st.cache_resource
def get_dhan_client_v299():
    return DhanMarketData()

client = get_dhan_client_v299()

# --- SIDEBAR ---
st.sidebar.title("⚙️ Engine Controls")
ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
expiry_input = st.sidebar.text_input("Target Expiry Date (YYYY-MM-DD)", value=(ist_now.date() + timedelta((1 - ist_now.date().weekday()) % 7)).strftime("%Y-%m-%d"))
live_feed = st.sidebar.toggle("🔴 Auto-Refresh Feed", value=True)
refresh_rate = st.sidebar.slider("Refresh Speed (Seconds)", 3, 60, 5)

if st.sidebar.button("🔄 Reset Baseline Memory"):
    if 'baseline' in st.session_state: del st.session_state['baseline']
    if 'active_alerts' in st.session_state: st.session_state.active_alerts = []
    st.sidebar.success("Memory Reset!")

# --- DATA PIPELINE (Phase 10: Performance) ---
api_start = time.time()
ltp, raw_response = client.get_live_option_chain(expiry_date=expiry_input)
api_latency = (time.time() - api_start) * 1000

if ltp is None or not raw_response:
    st.error("Waiting for Data...")
    st.stop()
    
df = client.process_oc_to_dataframe(raw_response)
if ltp == 0: ltp = df.loc[(df['CE_LTP'] - df['PE_LTP']).abs().idxmin(), 'Strike']
df_filtered = df[(df['Strike'] >= ltp - 600) & (df['Strike'] <= ltp + 600)].copy()

calc_start = time.time()
overall_pcr, atm_pcr = calculate_advanced_pcr(df_filtered, ltp)
max_pain = calculate_max_pain(df_filtered)
exposures = calculate_exposures(df_filtered, ltp)
vp = calculate_volume_profile(df_filtered)

current_total_oi = df_filtered['CE_OI'].sum() + df_filtered['PE_OI'].sum()

if 'baseline' not in st.session_state:
    st.session_state.baseline = {'ltp': ltp, 'oi': current_total_oi, 'pcr': overall_pcr, 'iv': 15.0, 'time': time.time()}

vol = analyze_volatility(df_filtered, ltp, st.session_state.baseline['ltp'], expiry_input)
st.session_state.baseline['iv'] = vol['atm_iv']

smart_money = analyze_smart_money(
    current_price=ltp, prev_price=st.session_state.baseline['ltp'],
    current_oi=current_total_oi, prev_oi=st.session_state.baseline['oi'],
    current_pcr=overall_pcr, prev_pcr=st.session_state.baseline['pcr'],
    current_iv=vol['atm_iv'], prev_iv=st.session_state.baseline['iv']
)

structure = analyze_market_structure(exposures['net_gex'], overall_pcr, smart_money['flow'], ltp, st.session_state.baseline['ltp'], vp['total_vol'])
dec = generate_institutional_decision(ltp, st.session_state.baseline['ltp'], overall_pcr, exposures['net_gex'], exposures['net_dex'], vol['expected_move'], smart_money['flow'])
calc_latency = (time.time() - calc_start) * 1000

# Phase 7 & 8: Log to DB
conn = sqlite3.connect('quant_engine.db')
conn.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?, ?)", (ist_now.strftime('%H:%M:%S'), ltp, dec['score'], dec['confidence'], structure['regime'], dec['signal']))
conn.commit()
conn.close()

# ==========================================
# PHASE 5: TOP RIBBON
# ==========================================
st.markdown("""
<style>
.rib { background: #1E1E2E; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #333; }
.rib-t { font-size: 0.85em; color: #888; text-transform: uppercase; letter-spacing: 1px; }
.rib-v { font-size: 1.4em; font-weight: bold; color: #FFF; }
.card { background: #161824; padding: 15px; border-radius: 8px; border: 1px solid #333; height: 100%; }
.bar-bg { width: 100%; background: #222; border-radius: 5px; height: 12px; margin-top: 5px;}
.bar-fg { height: 100%; border-radius: 5px; }
.matrix-row { display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding: 8px 0; }
.target-box { background: #222536; padding: 10px; border-radius: 6px; text-align: center; flex: 1; margin: 0 4px; }
.health-footer { background: #0E1117; border-top: 1px solid #333; padding: 8px; text-align: center; font-family: monospace; font-size: 0.85em; color: #888; margin-top: 30px;}
</style>
""", unsafe_allow_html=True)

r1, r2, r3, r4, r5, r6 = st.columns(6)
with r1: st.markdown(f"<div class='rib'><div class='rib-t'>Spot</div><div class='rib-v'>₹{ltp:,.0f}</div></div>", unsafe_allow_html=True)
with r2: st.markdown(f"<div class='rib'><div class='rib-t'>Inst. Score</div><div class='rib-v' style='color:{dec['color']}'>{dec['score']}/100</div></div>", unsafe_allow_html=True)
with r3: st.markdown(f"<div class='rib'><div class='rib-t'>Confidence</div><div class='rib-v'>{dec['confidence']}%</div></div>", unsafe_allow_html=True)
with r4: st.markdown(f"<div class='rib'><div class='rib-t'>Market Regime</div><div class='rib-v' style='color:{structure['color']}; font-size:1.1em;'>{structure['regime']}</div></div>", unsafe_allow_html=True)
with r5: st.markdown(f"<div class='rib'><div class='rib-t'>Net GEX</div><div class='rib-v'>{'🟢' if exposures['net_gex']>0 else '🔴'} {exposures['net_gex']/1e7:,.1f} Cr</div></div>", unsafe_allow_html=True)
with r6: st.markdown(f"<div class='rib'><div class='rib-t'>Expected Move</div><div class='rib-v'>±{vol['expected_move']:.0f}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# PHASE 5: 3-PANEL INSTITUTIONAL LAYOUT
# ==========================================
c_left, c_center, c_right = st.columns([1.2, 2.2, 1.2])

# --- LEFT PANEL: STRUCTURE ---
with c_left:
    st.markdown(f"""
<div class='card'>
<div style='color:#888; font-size:0.9em; letter-spacing:1px; margin-bottom:15px;'>MARKET INTELLIGENCE</div>
<div style='margin-bottom:15px;'>
    <div style='display:flex; justify-content:space-between;'><span>Trend Strength</span><span style='color:#00E676;'>{structure['trend_label']} ({structure['trend_strength']}/100)</span></div>
    <div class='bar-bg'><div class='bar-fg' style='width:{structure['trend_strength']}%; background:#00E676;'></div></div>
</div>
<hr style='border-color:#333;'>
<div style='color:#888; font-size:0.8em;'>VALUE AREA (70% VOL)</div>
<div style='display:flex; justify-content:space-between; margin-top:5px;'><span>VAH</span><span style='color:#00E676;'>₹{vp['vah']:.0f}</span></div>
<div style='display:flex; justify-content:space-between;'><span>POC</span><span style='color:#FFF; font-weight:bold;'>₹{vp['poc']:.0f}</span></div>
<div style='display:flex; justify-content:space-between;'><span>VAL</span><span style='color:#FF3D00;'>₹{vp['val']:.0f}</span></div>
<hr style='border-color:#333;'>
<div style='display:flex; justify-content:space-between;'><span>Flow</span><span style='color:{smart_money["flow_color"]};'>{smart_money["flow"]}</span></div>
</div>
""", unsafe_allow_html=True)

# --- CENTER PANEL: DECISION & PLANNER ---
with c_center:
    matrix_html = "".join([f"<div class='matrix-row'><span>{k}</span><span style='color:{'#00E676' if v=='✓' else '#FF3D00'}; font-weight:bold;'>{v}</span></div>" for k, v in dec['reasons'].items()])
    
    st.markdown(f"""
<div class='card' style='border-left: 4px solid {dec['color']};'>
<div style='display:flex; justify-content:space-between; align-items:center;'>
    <div>
        <h2 style='margin:0; color:{dec['color']};'>{dec['signal']}</h2>
        <span style='color:#888; font-size:0.9em;'>Algorithmic Trade Planner</span>
    </div>
    <div style='text-align:right;'>
        <div style='font-size:2em; font-weight:bold;'>{dec['score']}</div>
        <div style='color:#888; font-size:0.8em;'>SCORE</div>
    </div>
</div>

<div style='margin-top:20px; background:#0E1117; padding:15px; border-radius:8px;'>
    <div style='color:#888; font-size:0.8em; margin-bottom:10px; text-transform:uppercase;'>Decision Matrix (Why?)</div>
    {matrix_html}
</div>

<div style='display:flex; justify-content:space-between; margin-top:20px;'>
    <div class='target-box'>
        <div style='color:#888; font-size:0.8em;'>ENTRY</div>
        <div style='font-size:1.2em; font-weight:bold;'>₹{dec['entry']:.0f}</div>
    </div>
    <div class='target-box'>
        <div style='color:#888; font-size:0.8em;'>STOP LOSS</div>
        <div style='font-size:1.2em; font-weight:bold; color:#FF3D00;'>₹{dec['sl']:.0f}</div>
    </div>
    <div class='target-box'>
        <div style='color:#888; font-size:0.8em;'>TARGET 1</div>
        <div style='font-size:1.2em; font-weight:bold; color:#00E676;'>₹{dec['t1']:.0f}</div>
    </div>
    <div class='target-box'>
        <div style='color:#888; font-size:0.8em;'>TARGET 2</div>
        <div style='font-size:1.2em; font-weight:bold; color:#00E676;'>₹{dec['t2']:.0f}</div>
    </div>
    <div class='target-box'>
        <div style='color:#888; font-size:0.8em;'>RISK:REWARD</div>
        <div style='font-size:1.2em; font-weight:bold;'>{dec['rr']}</div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

# --- RIGHT PANEL: PROBABILITIES ---
with c_right:
    st.markdown(f"""
<div class='card'>
<div style='color:#888; font-size:0.9em; letter-spacing:1px; margin-bottom:20px;'>PROBABILITY GAUGES</div>

<div style='margin-bottom: 15px;'>
    <div style='display:flex; justify-content:space-between;'><span style='color:#00E676; font-weight:bold;'>BULLISH</span><span>{dec["bull_prob"]}%</span></div>
    <div class='bar-bg'><div class='bar-fg' style='width: {dec["bull_prob"]}%; background: #00E676;'></div></div>
</div>

<div style='margin-bottom: 15px;'>
    <div style='display:flex; justify-content:space-between;'><span style='color:#FFC107; font-weight:bold;'>SIDEWAYS</span><span>{dec["side_prob"]}%</span></div>
    <div class='bar-bg'><div class='bar-fg' style='width: {dec["side_prob"]}%; background: #FFC107;'></div></div>
</div>

<div style='margin-bottom: 15px;'>
    <div style='display:flex; justify-content:space-between;'><span style='color:#FF3D00; font-weight:bold;'>BEARISH</span><span>{dec["bear_prob"]}%</span></div>
    <div class='bar-bg'><div class='bar-fg' style='width: {dec["bear_prob"]}%; background: #FF3D00;'></div></div>
</div>
<hr style='border-color:#333;'>
<div style='color:{smart_money["div_color"]}; font-size:0.9em; text-align:center;'>{smart_money["divergence"]}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

c_chart, c_table = st.columns([2, 2])
with c_chart: 
    st.plotly_chart(render_oi_heatmap(df_filtered), use_container_width=True)
with c_table:
    st.markdown("### Institutional Greeks & Volume")
    atm_df = df_filtered.iloc[(df_filtered['Strike'] - ltp).abs().argsort()[:7]].sort_values('Strike')
    st.dataframe(atm_df[['Strike', 'CE_LTP', 'CE_Volume', 'CE_Gamma', 'PE_Gamma', 'PE_Volume', 'PE_LTP']], hide_index=True, use_container_width=True)

# Alerts
if 'active_alerts' not in st.session_state: st.session_state.active_alerts = []
current_alerts = check_smart_alerts(ltp, st.session_state.baseline['ltp'], exposures['gamma_flip'], smart_money['flow'], smart_money['divergence'], overall_pcr, st.session_state.baseline['pcr'])
for alert in current_alerts:
    if alert['msg'] not in st.session_state.active_alerts:
        st.toast(alert['msg'], icon=alert['icon'])
        send_telegram_alert(alert['msg'], alert['icon'])
        st.session_state.active_alerts.append(alert['msg'])
if len(st.session_state.active_alerts) > 10: st.session_state.active_alerts = st.session_state.active_alerts[-5:]

# Phase 10: Diagnostics Footer
st.markdown(f"""
<div class='health-footer'>
<span>🟢 SYSTEM HEALTH: V2.99 | </span>
<span>Dhan API: <span style='color:#00E676;'>{api_latency:.1f} ms</span> | </span>
<span>Matrix Engine: <span style='color:#00E676;'>{calc_latency:.1f} ms</span> | </span>
<span>History Log: <span style='color:#00E676;'>Active</span></span>
</div>
""", unsafe_allow_html=True)

if live_feed:
    time.sleep(refresh_rate)
    st.rerun()
