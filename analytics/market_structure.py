def analyze_market_structure(net_gex, pcr, flow, ltp, baseline_ltp, total_vol):
    """
    PHASE 1: Market Regime & Trend Strength Classifier
    """
    # Trend Strength (0-100) Formula
    price_momentum = abs((ltp - baseline_ltp) / baseline_ltp) * 10000 
    pcr_strength = abs(pcr - 1.0) * 50
    gex_strength = min(30, abs(net_gex) / 10000000)
    
    trend_strength = int(min(100, price_momentum + pcr_strength + gex_strength + (total_vol/1000000)))
    
    if trend_strength > 80: trend_label = "Very Strong"
    elif trend_strength > 60: trend_label = "Strong"
    elif trend_strength > 40: trend_label = "Moderate"
    else: trend_label = "Weak"

    # Regime Classification
    confidence = min(99, trend_strength + 20)
    
    if net_gex > 0:
        if pcr > 1.2 and ltp > baseline_ltp:
            regime, color = "Mean Reversion (Bullish)", "#00E676"
        elif pcr < 0.8 and ltp < baseline_ltp:
            regime, color = "Mean Reversion (Bearish)", "#FF3D00"
        else:
            regime, color = "Gamma Pinning (Range Day)", "#FFC107"
    else:
        if pcr > 1.0 and "Long" in flow and ltp > baseline_ltp:
            regime, color = "Trend Day (Up)", "#00E676"
        elif pcr < 1.0 and "Short" in flow and ltp < baseline_ltp:
            regime, color = "Trend Day (Down)", "#FF3D00"
        elif "Unwinding" in flow or "Covering" in flow:
            regime, color = "Volatility Expansion", "#FFC107"
        else:
            regime, color = "Breakout Watch", "#FFC107"

    return {
        "regime": regime,
        "color": color,
        "trend_strength": trend_strength,
        "trend_label": trend_label,
        "confidence": confidence
    }
    from typing import Dict, Any
import numpy as np

def analyze_market_structure(
    net_gex: float, 
    pcr: float, 
    flow_score: float, 
    ltp: float, 
    vwap: float, 
    orh: float, 
    orl: float, 
    max_pain: float, 
    atr: float
) -> Dict[str, Any]:
    """
    Expands market structure analysis using VWAP, Opening Ranges, Max Pain distance, and ATR.
    """
    vwap_dist = ltp - vwap
    pain_dist = ((ltp - max_pain) / max_pain) * 100
    
    # Trend Strength components
    vwap_strength = min(30, max(0, (vwap_dist / (atr if atr > 0 else 50)) * 15 + 15))
    flow_strength = flow_score * 0.3
    gex_strength = min(30, abs(net_gex) / 20000000)
    pcr_strength = abs(pcr - 1.0) * 20

    trend_strength = int(min(100, vwap_strength + flow_strength + gex_strength + pcr_strength))
    
    if trend_strength > 75: trend_label = "Very Strong"
    elif trend_strength > 55: trend_label = "Strong"
    elif trend_strength > 35: trend_label = "Moderate"
    else: trend_label = "Weak"

    # Opening Range Context
    if ltp > orh:
        or_status = "Opening Range Breakout (Bullish)"
    elif ltp < orl:
        or_status = "Opening Range Breakdown (Bearish)"
    else:
        or_status = "Inside Opening Range"

    # Regime Classification
    if net_gex > 0:
        regime, color = ("Mean Reversion (Range Day)", "#FFC107") if abs(vwap_dist) < (atr * 0.5) else ("Volatility Expansion", "#00E676")
    else:
        if ltp > vwap and pcr > 1.0:
            regime, color = "Trend Day (Bullish)", "#00E676"
        elif ltp < vwap and pcr < 1.0:
            regime, color = "Trend Day (Bearish)", "#FF3D00"
        else:
            regime, color = "Breakout Watch", "#FFC107"

    return {
        "regime": regime,
        "color": color,
        "trend_strength": trend_strength,
        "trend_label": trend_label,
        "or_status": or_status,
        "pain_dist": pain_dist
    }
