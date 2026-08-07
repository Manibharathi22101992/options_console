def analyze_smart_money(current_price, prev_price, current_oi, prev_oi, current_pcr, prev_pcr, current_iv, prev_iv):
    """
    SPRINT 4 & 7: Smart Money Flow and Advanced Divergence Engine
    Now tracks Volatility Crush and Expansion to detect Institutional Traps.
    """
    if prev_price == 0 or prev_oi == 0:
        return {
            "flow": "Calibrating...", "flow_score": 0, "flow_color": "#888",
            "divergence": "Calibrating...", "div_score": 0, "div_color": "#888"
        }
        
    price_delta = current_price - prev_price
    oi_delta = current_oi - prev_oi
    pcr_delta = current_pcr - prev_pcr
    iv_delta = current_iv - prev_iv
    
    # ----------------------------------------
    # FLOW ENGINE
    # ----------------------------------------
    if price_delta > 0 and oi_delta > 0:
        flow, f_score, f_color = "Long Build-Up", 85, "#00E676"
    elif price_delta < 0 and oi_delta > 0:
        flow, f_score, f_color = "Short Build-Up", 85, "#FF3D00"
    elif price_delta > 0 and oi_delta < 0:
        flow, f_score, f_color = "Short Covering", 72, "#00E676"
    elif price_delta < 0 and oi_delta < 0:
        flow, f_score, f_color = "Long Unwinding", 72, "#FF3D00"
    else:
        flow, f_score, f_color = "Consolidation", 50, "#FFC107"

    # ----------------------------------------
    # SPRINT 7: ADVANCED DIVERGENCE ENGINE
    # ----------------------------------------
    divergence = "No Divergence Detected"
    d_score = 50
    d_color = "#888"

    # 1. Volatility Crush Divergence (Price Up, IV Down heavily)
    if price_delta > 0 and iv_delta < -0.5:
        divergence = "IV Crush (Upside Capped/Call Selling)"
        d_score = 85
        d_color = "#FFC107"
        
    # 2. Panic Divergence (Price Down, IV Up, PCR Down)
    elif price_delta < 0 and iv_delta > 0.5 and pcr_delta < 0:
        divergence = "Panic Put Buying (Volatility Expansion)"
        d_score = 88
        d_color = "#FF3D00"
        
    # 3. Hidden Accumulation (Price Down, PCR Up)
    elif price_delta < 0 and pcr_delta > 0:
        divergence = "Bullish Hidden Accumulation"
        d_score = 84
        d_color = "#00E676"
        
    # 4. Weak Rally (Price Up, PCR Down, OI Flat/Down)
    elif price_delta > 0 and pcr_delta < 0 and oi_delta <= 0:
        divergence = "Bearish Divergence (Weak Rally)"
        d_score = 82
        d_color = "#FF3D00"

    return {
        "flow": flow, "flow_score": f_score, "flow_color": f_color,
        "divergence": divergence, "div_score": d_score, "div_color": d_color
    }
from typing import Dict, Any

def analyze_smart_money(
    current_price: float, 
    prev_price: float, 
    features: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes a continuous 0-100 Flow Score driven by OI velocity, volume velocity,
    price momentum, and premium expansion.
    """
    spot_vel = features.get("spot_velocity", 0.0)
    oi_accel = features.get("oi_acceleration", 0.0)
    vol_vel = features.get("volume_velocity", 0.0)
    prem_exp = features.get("premium_expansion", 0.0)

    # Data-driven score calculation (Normalized 0 to 100)
    raw_score = 50.0 + (spot_vel * 0.5) + (oi_accel / 100000.0) + (vol_vel / 500000.0) + (prem_exp * 2.0)
    flow_score = float(max(0.0, min(100.0, raw_score)))

    if flow_score >= 65.0:
        flow, flow_color = "Institutional Accumulation (Long)", "#00E676"
    elif flow_score <= 35.0:
        flow, flow_color = "Institutional Distribution (Short)", "#FF3D00"
    else:
        flow, flow_color = "Neutral / Two-Way Flow", "#FFC107"

    # Divergence Engine integration
    iv_vel = features.get("iv_velocity", 0.0)
    if spot_vel > 0 and iv_vel < -0.2:
        divergence = "IV Crush / Capped Upside"
        div_color = "#FFC107"
    elif spot_vel < 0 and iv_vel > 0.2:
        divergence = "Panic Hedging / Vol Expansion"
        div_color = "#FF3D00"
    else:
        divergence = "No Structural Divergence"
        div_color = "#888"

    return {
        "flow": flow,
        "flow_score": flow_score,
        "flow_color": flow_color,
        "divergence": divergence,
        "div_color": div_color
    }
