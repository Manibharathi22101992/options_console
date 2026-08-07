def generate_institutional_decision(ltp, pcr, net_gex, net_dex, expected_move, max_pain, flow):
    """
    SPRINT 1: Continuous Scoring Engine
    Calculates a weighted Institutional Score from 0 (Max Bear) to 100 (Max Bull).
    """
    # ---------------------------------------------------------
    # 1. COMPONENT SCORING (0 to 100 scale, 50 = Neutral)
    # ---------------------------------------------------------
    
    # PCR Score (Center 1.0 = 50. Ranges roughly 0.5 to 1.5)
    pcr_score = max(0, min(100, 50 + ((pcr - 1.0) * 100)))

    # Gamma Score (Trending vs Range logic based on Max Pain deviation)
    dist_to_pain = (ltp - max_pain) / max_pain
    gex_score = 50 
    if net_gex < 0: # If dealers are short Gamma, trend is amplified
        gex_score = 50 + (dist_to_pain * 10000) # Positive if above pain, negative if below
    gex_score = max(0, min(100, gex_score))

    # Delta Score (Negative DEX = Dealers must buy to hedge = Bullish)
    dex_normalized = max(-100, min(100, net_dex / 10000000)) 
    dex_score = max(0, min(100, 50 - (dex_normalized / 2)))

    # Smart Money Flow Score
    flow_score = 50
    if "Long Build-Up" in flow: flow_score = 90
    elif "Short Covering" in flow: flow_score = 75
    elif "Short Build-Up" in flow: flow_score = 10
    elif "Long Unwinding" in flow: flow_score = 25

    # ---------------------------------------------------------
    # 2. WEIGHTED INSTITUTIONAL SCORE
    # ---------------------------------------------------------
    # Weights: Flow (35%), Delta (25%), Gamma (20%), PCR (20%)
    inst_score = (flow_score * 0.35) + (dex_score * 0.25) + (gex_score * 0.20) + (pcr_score * 0.20)
    inst_score = int(inst_score)

    # ---------------------------------------------------------
    # 3. PROBABILITY ENGINE (SPRINT 10)
    # ---------------------------------------------------------
    if net_gex > 0:
        # Range Bound Environment: High Sideways probability
        side_prob = min(70, 40 + (net_gex / 20000000))
    else:
        # Trending Environment: Low Sideways probability
        side_prob = 15

    directional_remainder = 100 - side_prob
    bull_prob = directional_remainder * (inst_score / 100)
    bear_prob = directional_remainder - bull_prob

    # ---------------------------------------------------------
    # 4. ADVANCED TRADE EXECUTION (SPRINT 11)
    # ---------------------------------------------------------
    if inst_score >= 65:
        signal = "BUY CE (STRONG BULLISH)"
        color = "#00E676"
    elif inst_score >= 55:
        signal = "BUY CE (BULLISH LEAN)"
        color = "#00E676"
    elif inst_score <= 35:
        signal = "BUY PE (STRONG BEARISH)"
        color = "#FF3D00"
    elif inst_score <= 45:
        signal = "BUY PE (BEARISH LEAN)"
        color = "#FF3D00"
    else:
        signal = "WAIT / SELL STRANGLE (RANGE BOUND)"
        color = "#FFC107"

    em = expected_move if expected_move > 20 else 50
    
    if inst_score > 50:
        entry = ltp
        target_1 = ltp + (em * 0.5)
        target_2 = ltp + em
        sl = ltp - (em * 0.4)
        rr = f"1 : {((target_2 - entry) / (entry - sl)):.1f}"
    else:
        entry = ltp
        target_1 = ltp - (em * 0.5)
        target_2 = ltp - em
        sl = ltp + (em * 0.4)
        rr = f"1 : {((entry - target_2) / (sl - entry)):.1f}"

    return {
        "bull_prob": int(bull_prob), "bear_prob": int(bear_prob), "side_prob": int(side_prob),
        "score": inst_score, "signal": signal, "entry": entry,
        "target_1": target_1, "target_2": target_2, "sl": sl,
        "rr": rr, "color": color
    }
