import os
import requests
import logging

logger = logging.getLogger(__name__)

# Fetch credentials from environment (Streamlit Secrets or .env)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_telegram_alert(msg, icon):
    """Pushes the alert to your Telegram App if credentials are set."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"{icon} <b>QUANT ENGINE ALERT</b>\n\n{msg}",
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")

def check_smart_alerts(ltp, prev_ltp, gamma_flip, flow, divergence, pcr, prev_pcr):
    """
    Phase 12: Smart Alerts Engine
    Detects critical market shifts and generates institutional notifications.
    """
    alerts = []
    
    # 1. Gamma Flip Alert (Critical Trend Reversal)
    if prev_ltp < gamma_flip and ltp >= gamma_flip:
        alerts.append({"msg": f"LTP crossed ABOVE Gamma Flip (₹{gamma_flip:,.0f}). Bullish Gamma Squeeze possible!", "icon": "🚀"})
    elif prev_ltp > gamma_flip and ltp <= gamma_flip:
        alerts.append({"msg": f"LTP crossed BELOW Gamma Flip (₹{gamma_flip:,.0f}). Bearish Volatility Expansion!", "icon": "🩸"})

    # 2. Smart Money Flow Alerts (Aggressive Positioning)
    if "Build-Up" in flow:
        direction = "🟢 Bullish" if "Long" in flow else "🔴 Bearish"
        alerts.append({"msg": f"Aggressive Smart Money Flow: {direction} {flow}", "icon": "🏦"})

    # 3. Divergence Alerts (Hidden Traps)
    if "Divergence" in divergence or "Hidden" in divergence:
        alerts.append({"msg": f"Trap Detected: {divergence}", "icon": "⚠️"})

    # 4. PCR Reversal Alerts
    if prev_pcr < 1.0 and pcr >= 1.0:
        alerts.append({"msg": f"PCR crossed above 1.0 (Bullish Shift)\nCurrent PCR: {pcr:.2f}", "icon": "🐂"})
    elif prev_pcr > 1.0 and pcr <= 1.0:
        alerts.append({"msg": f"PCR crossed below 1.0 (Bearish Shift)\nCurrent PCR: {pcr:.2f}", "icon": "🐻"})

    return alerts
