def analyze_market_structure(net_gex, pcr, flow):
    """
    Phase 1: Market Structure Engine
    Determines if today is a Trend Day, Range Day, Short Covering, etc.
    Positive Gamma = Dealers suppress volatility (Range/Mean Reversion)
    Negative Gamma = Dealers amplify volatility (Trend/Breakout)
    """
    confidence = 50
    regime = "Consolidation (Range Day)"
    color = "#FFC107" # Yellow

    if net_gex > 0:
        # Market Makers are Long Gamma (Selling rips, buying dips -> Range Bound)
        if pcr > 1.2:
            regime = "Mean Reversion (Bullish Bias)"
            confidence = 75
            color = "#00E676"
        elif pcr < 0.8:
            regime = "Mean Reversion (Bearish Bias)"
            confidence = 75
            color = "#FF3D00"
        else:
            regime = "Choppy / Range Bound"
            confidence = 85
            color = "#FFC107"
    else:
        # Market Makers are Short Gamma (Buying rips, selling dips -> Trend/Breakout)
        if pcr > 1.0 and "Long" in flow:
            regime = "Trend Day (Bullish)"
            confidence = 88
            color = "#00E676"
        elif pcr < 1.0 and "Short" in flow:
            regime = "Trend Day (Bearish)"
            confidence = 88
            color = "#FF3D00"
        elif "Covering" in flow:
            regime = "Short Covering Rally"
            confidence = 82
            color = "#00E676"
        elif "Unwinding" in flow:
            regime = "Long Unwinding (Bearish)"
            confidence = 82
            color = "#FF3D00"
        else:
            regime = "Volatility Expansion (Breakout Pending)"
            confidence = 70
            color = "#FFC107"

    return {
        "regime": regime,
        "confidence": confidence,
        "color": color
    }
