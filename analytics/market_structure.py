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
