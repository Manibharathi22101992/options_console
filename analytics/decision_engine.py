def generate_institutional_decision(ltp, pcr, net_gex, net_dex, expected_move, max_pain, flow):
    """
    Phases 8, 9, 10: Institutional Score, Probabilities, and Trade Execution Math.
    Calculates exact targets and stops based on Black-Scholes expected move.
    """
    # 1. Calculate Probabilities
    bull_prob = 33.0
    bear_prob = 33.0
    side_prob = 34.0

    # Gamma Exposure Impact (Trend vs Range)
    if net_gex > 0:
        side_prob += 25
        bull_prob -= 12.5
        bear_prob -= 12.5
    else:
        side_prob -= 15
        bull_prob += 7.5
        bear_prob += 7.5

    # PCR Impact
    if pcr > 1.1:
        bull_prob += 15
        bear_prob -= 10
    elif pcr < 0.8:
        bear_prob += 15
        bull_prob -= 10

    # Dealer Hedging Impact (DEX)
    if net_dex < 0:
        bull_prob += 10
        bear_prob -= 5
    else:
        bear_prob += 10
        bull_prob -= 5
        
    # Smart Money Impact
    if "Long Build-Up" in flow or "Short Covering" in flow:
        bull_prob += 10
        bear_prob -= 10
    elif "Short Build-Up" in flow or "Long Unwinding" in flow:
        bear_prob += 10
        bull_prob -= 10

    # Normalize to 100%
    total = max(1, bull_prob + bear_prob + side_prob)
    bull_prob = max(5, int((bull_prob / total) * 100))
    bear_prob = max(5, int((bear_prob / total) * 100))
    side_prob = 100 - bull_prob - bear_prob
    
    # 2. Institutional Score
    score = max(bull_prob, bear_prob, side_prob)

    # 3. Trade Execution Setup
    em = expected_move if expected_move > 20 else 50 # Minimum move buffer

    if bull_prob > 50 and side_prob < 40:
        signal = "BUY CE (BULLISH TREND)"
        entry = ltp
        target = ltp + em
        sl = ltp - (em / 2)
        rr = "1 : 2.0"
        color = "#00E676"
    elif bear_prob > 50 and side_prob < 40:
        signal = "BUY PE (BEARISH TREND)"
        entry = ltp
        target = ltp - em
        sl = ltp + (em / 2)
        rr = "1 : 2.0"
        color = "#FF3D00"
    else:
        signal = "WAIT / SELL STRANGLE (RANGE BOUND)"
        entry = ltp
        target = ltp + em
        sl = ltp - em
        rr = "Delta Neutral"
        color = "#FFC107"

    return {
        "bull_prob": bull_prob,
        "bear_prob": bear_prob,
        "side_prob": side_prob,
        "score": score,
        "signal": signal,
        "entry": entry,
        "target": target,
        "sl": sl,
        "rr": rr,
        "color": color
    }
