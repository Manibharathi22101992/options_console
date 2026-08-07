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
from analytics.decision_engine import generate_institutional_decision
from analytics.market_structure import analyze_market_structure
from analytics.alerts import check_smart_alerts, send_telegram_alert
from ui.components import render_oi_heatmap
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
def get_dhan_client_v19():
    return DhanMarketData()

client = get_dhan_client_v19()

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
    if 'active_alerts' in st.session_state:
        st.session_state.active_alerts = []
    st.sidebar.success("Memory & Alerts Reset!")

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
volatility = analyze_volatility(df_filtered, ltp, expiry_input)

# --- STATE MEMORY ---
current_total_oi = df_filtered['CE_OI'].sum() + df_filtered['PE_OI'].sum()
if 'baseline' not in st.session_state:
    st.session_state.baseline = {'ltp': ltp, 'oi': current_total_oi, 'pcr': overall_pcr, 'time': time.time()}
    
smart_money = analyze_smart_money(
    current_price=ltp, prev_price=st.session_state.baseline['ltp'],
    current_oi=current_total_oi, prev_oi=st.session_state.baseline['oi'],
    current_pcr=overall_pcr, prev_pcr=st.session_state.baseline['pcr']
)

decision = generate_institutional_decision(
    ltp, overall_pcr, exposures['net_gex'], exposures['net_dex'], 
    volatility['expected_move'], max_pain, smart_money['flow']
)

structure = analyze_market_structure(exposures['net_gex'], overall_pcr, smart_money['flow'])

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
.sm-card { padding: 15px; border-radius: 10px; background-color: #1E1E2E; border: 1px solid #333; text-align: center; height: 100%;}

.trade-setup { background-color: #161824; border: 1px solid #333; border-radius: 8px; padding: 15px; margin-top: 10px; }
.trade-grid { display: flex; justify-content: space-between; text-align: center; margin-top: 15px; }
.trade-box { flex: 1; margin: 0 5px; background: #222536; padding: 10px; border-radius: 6px; }
.trade-label { font-size: 0.8em; color: #888; text-transform: uppercase; }
.trade-value { font-size: 1.3em; font-weight: bold; color: #FFF; }

.prob-bar-container { width: 100%; background-color: #222; border-radius: 5px; margin-top: 5px; height: 18px; }
.prob-bar { height: 100%; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ Institutional Decision Intelligence")
st.caption(f"IST: {ist_now.strftime('%H:%M:%S')} | Target Expiry: {expiry_input}")

r1, r2, r3, r4, r5, r6, r7 = st.columns(7)
with r1: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Spot</div><div class='ribbon-val'>₹{ltp:,.0f}</div></div>", unsafe_allow_html=True)
with r2: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>PCR</div><div class='ribbon-val'>{overall_pcr:.2f}</div></div>", unsafe_allow_html=True)
with r3: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Max Pain</div><div class='ribbon-val'>₹{max_pain:,.0f}</div></div>", unsafe_allow_html=True)
with r4: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Net GEX</div><div class='ribbon-val {'pos-gex' if exposures['net_gex'] > 0 else 'neg-gex'}'>{exposures['net_gex']/1e7:,.1f} Cr</div></div>", unsafe_allow_html=True)
with r5: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Expected Move</div><div class='ribbon-val'>±{volatility['expected_move']:.0f}</div></div>", unsafe_allow_html=True)
with r6: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Dealer Regime</div><div class='ribbon-val' style='font-size:1.1em;'>{'Long Gamma' if exposures['net_gex'] > 0 else 'Short Gamma'}</div></div>", unsafe_allow_html=True)
with r7: st.markdown(f"<div class='ribbon-metric'><div class='ribbon-title'>Hedging</div><div class='ribbon-val' style='font-size:1.1em;'>{'Bullish' if exposures['net_dex'] < 0 else 'Bearish'}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# MIDDLE ROW: TRADE EXECUTION & PROBABILITY
# ==========================================
m1, m2, m3 = st.columns([1.5, 2.5, 1.2])

with m1:
    st.markdown(f"""
<div class='sm-card'>
<div style='color: #888; font-size: 0.9em; letter-spacing: 1px;'>MARKET STRUCTURE</div>
<div style='color: {structure["color"]}; font-size: 1.5em; font-weight: bold; margin-top: 10px;'>{structure["regime"]}</div>
<div style='color: #AAA; font-size: 0.9em;'>Confidence: {structure["confidence"]}%</div>
<hr style="border-color: #333; margin: 15px 0;">
<div style='color: #888; font-size: 0.8em; text-transform: uppercase;'>Institutional Score (0-100)</div>
<div style='color: {decision["color"]}; font-size: 3em; font-weight: bold;'>{decision["score"]}</div>
<div style='color: {decision["color"]}; font-size: 1em; margin-bottom: 10px;'>{decision["signal"].split('(')[-1].replace(')','')}</div>
<div style='padding: 5px; background: rgba(0,0,0,0.2); border-radius: 5px;'>
<div style='color: {smart_money["flow_color"]}; font-size: 0.9em; font-weight: bold;'>{smart_money["flow"]}</div>
<div style='color: {smart_money["div_color"]}; font-size: 0.8em;'>{smart_money["divergence"]}</div>
</div>
</div>
""", unsafe_allow_html=True)

with m2:
    st.markdown(f"""
<div class='trade-setup'>
<h3 style='margin:0; color:{decision["color"]};'>{decision["signal"]}</h3>
<p style='margin:0; color:#888; font-size:0.9em;'>Algorithmic Trade Recommendation (Based on BS Expected Move)</p>
<div class='trade-grid' style='margin-top: 20px;'>
<div class='trade-box'>
<div class='trade-label'>Entry</div>
<div class='trade-value'>₹{decision["entry"]:,.0f}</div>
</div>
<div class='trade-box'>
<div class='trade-label'>Stop Loss</div>
<div style='color:#FF3D00;' class='trade-value'>₹{decision["sl"]:,.0f}</div>
</div>
<div class='trade-box'>
<div class='trade-label'>Target 1</div>
<div style='color:#00E676;' class='trade-value'>₹{decision["target_1"]:,.0f}</div>
</div>
<div class='trade-box'>
<div class='trade-label'>Target 2</div>
<div style='color:#00E676;' class='trade-value'>₹{decision["target_2"]:,.0f}</div>
</div>
<div class='trade-box'>
<div class='trade-label'>Risk:Reward</div>
<div class='trade-value'>{decision["rr"]}</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

with m3:
    st.markdown(f"""
<div class='sm-card' style='text-align: left; padding: 20px;'>
<div style='color: #888; font-size: 0.9em; letter-spacing: 1px; text-align: center; margin-bottom: 15px;'>PROBABILITIES</div>
<div style='margin-bottom: 10px;'>
<span style='color: #00E676; font-weight: bold; font-size: 0.9em;'>BULLISH ({decision["bull_prob"]}%)</span>
<div class='prob-bar-container'><div class='prob-bar' style='width: {decision["bull_prob"]}%; background-color: #00E676;'></div></div>
</div>
<div style='margin-bottom: 10px;'>
<span style='color: #FFC107; font-weight: bold; font-size: 0.9em;'>SIDEWAYS ({decision["side_prob"]}%)</span>
<div class='prob-bar-container'><div class='prob-bar' style='width: {decision["side_prob"]}%; background-color: #FFC107;'></div></div>
</div>
<div style='margin-bottom: 10px;'>
<span style='color: #FF3D00; font-weight: bold; font-size: 0.9em;'>BEARISH ({decision["bear_prob"]}%)</span>
<div class='prob-bar-container'><div class='prob-bar' style='width: {decision["bear_prob"]}%; background-color: #FF3D00;'></div></div>
</div>
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

# ==========================================
# PHASE 12: SMART ALERTS NOTIFICATION SYSTEM
# ==========================================
if 'active_alerts' not in st.session_state:
    st.session_state.active_alerts = []

current_alerts = check_smart_alerts(
    ltp, st.session_state.baseline['ltp'], exposures['gamma_flip'], 
    smart_money['flow'], smart_money['divergence'], overall_pcr, st.session_state.baseline['pcr']
)

for alert in current_alerts:
    if alert['msg'] not in st.session_state.active_alerts:
        st.toast(alert['msg'], icon=alert['icon'])
        send_telegram_alert(alert['msg'], alert['icon'])
        st.session_state.active_alerts.append(alert['msg'])

if len(st.session_state.active_alerts) > 10:
    st.session_state.active_alerts = st.session_state.active_alerts[-5:]

if live_feed:
    time.sleep(refresh_rate)
    st.rerun()
