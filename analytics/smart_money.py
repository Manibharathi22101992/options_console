def analyze_smart_money(current_price, prev_price, current_oi, prev_oi, current_pcr, prev_pcr):
    """
    Phase 4 & 5: Smart Money Flow and Divergence Engine
    Compares current state to baseline state to detect institutional activity.
    """
    # Guard against first-run empty baselines
    if prev_price == 0 or prev_oi == 0:
        return {
            "flow": "Calibrating...", "flow_score": 0, "flow_color": "#888",
            "divergence": "Calibrating...", "div_score": 0, "div_color": "#888"
        }
        
    price_delta = current_price - prev_price
    oi_delta = current_oi - prev_oi
    pcr_delta = current_pcr - prev_pcr
    
    # ----------------------------------------
    # PHASE 4: SMART MONEY FLOW (OI vs Price)
    # ----------------------------------------
    if price_delta > 0 and oi_delta > 0:
        flow = "Long Build-Up"
        f_score = 85
        f_color = "#00E676" # Bullish Green
    elif price_delta < 0 and oi_delta > 0:
        flow = "Short Build-Up"
        f_score = 85
        f_color = "#FF3D00" # Bearish Red
    elif price_delta > 0 and oi_delta < 0:
        flow = "Short Covering"
        f_score = 72
        f_color = "#00E676" 
    elif price_delta < 0 and oi_delta < 0:
        flow = "Long Unwinding"
        f_score = 72
        f_color = "#FF3D00"
    else:
        flow = "Consolidation"
        f_score = 50
        f_color = "#FFC107" # Yellow

    # ----------------------------------------
    # PHASE 5: DIVERGENCE ENGINE
    # ----------------------------------------
    divergence = "No Divergence Detected"
    d_score = 50
    d_color = "#888"

    # Bearish Divergence: Price rallying, but PCR and OI dropping (Weakness)
    if price_delta > 0 and pcr_delta < 0 and oi_delta <= 0:
        divergence = "Bearish Divergence (Weak Rally)"
        d_score = 82
        d_color = "#FF3D00"
        
    # Bullish Divergence: Price dropping, but PCR increasing (Hidden Put Selling)
    elif price_delta < 0 and pcr_delta > 0:
        divergence = "Bullish Hidden Accumulation"
        d_score = 84
        d_color = "#00E676"
        
    # Confirmation Trends
    elif price_delta > 0 and pcr_delta > 0:
        divergence = "Trend Confirmed (Bullish)"
        d_score = 90
        d_color = "#00E676"
        
    elif price_delta < 0 and pcr_delta < 0:
        divergence = "Trend Confirmed (Bearish)"
        d_score = 90
        d_color = "#FF3D00"

    return {
        "flow": flow,
        "flow_score": f_score,
        "flow_color": f_color,
        "divergence": divergence,
        "div_score": d_score,
        "div_color": d_color,
        "price_delta": price_delta,
        "oi_delta": oi_delta
    }
