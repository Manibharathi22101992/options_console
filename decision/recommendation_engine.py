import yaml
import os

def load_weights():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base_dir, 'config', 'weights.yaml'), 'r') as f:
            return yaml.safe_load(f)
    except Exception:
        return {"weights": {"flow": 0.35, "gamma": 0.20, "delta": 0.20, "pcr": 0.15, "vwap_proxy": 0.10}}

def generate_institutional_decision(ltp, baseline_ltp, pcr, net_gex, net_dex, expected_move, flow):
    """
    PHASES 3 & 4: Smart Decision Engine & Trade Planner
    Outputs probabilities, exact dynamic targets, and an Explainability Matrix.
    """
    config = load_weights()
    w = config['weights']
    
    # Component Scoring (0-100)
    pcr_score = max(0, min(100, 50 + ((pcr - 1.0) * 100)))
    gex_score = 50 + (10 if net_gex < 0 else -10)
    dex_score = max(0, min(100, 50 - (net_dex / 20000000)))
    
    if "Long Build-Up" in flow: flow_score = 90
    elif "Short Covering" in flow: flow_score = 70
    elif "Short Build-Up" in flow: flow_score = 10
    elif "Long Unwinding" in flow: flow_score = 30
    else: flow_score = 50
        
    vwap_proxy = 75 if ltp > baseline_ltp else 25

    # Weighted Institutional Score
    inst_score = int((flow_score * w['flow']) + (dex_score * w['delta']) + 
                     (gex_score * w['gamma']) + (pcr_score * w['pcr']) + 
                     (vwap_proxy * w['vwap_proxy']))

    # Probabilities
    side_prob = min(60, 30 + (net_gex / 20000000)) if net_gex > 0 else 15
    rem = 100 - side_prob
    bull_prob = rem * (inst_score / 100)
    bear_prob = rem - bull_prob
    
    confidence = int(abs(bull_prob - bear_prob))

    # Matrix Explanations (Why are we doing this?)
    reasons = {
        "Gamma Supportive": "✓" if (inst_score > 50 and net_gex < 0) or (inst_score < 50 and net_gex < 0) else "✗",
        "Delta Hedging Alignment": "✓" if (inst_score > 50 and net_dex < 0) or (inst_score < 50 and net_dex > 0) else "✗",
        "Smart Money Flow": "✓" if (inst_score > 50 and flow_score > 50) or (inst_score < 50 and flow_score < 50) else "✗",
        "Price > Baseline": "✓" if ltp > baseline_ltp else "✗"
    }

    # Signal & Dynamic Stops/Targets
    em = expected_move if expected_move > 20 else 50
    
    if inst_score >= 65:
        signal, color = "BUY CE (STRONG BULLISH)", "#00E676"
    elif inst_score >= 55:
        signal, color = "BUY CE (BULLISH LEAN)", "#00E676"
    elif inst_score <= 35:
        signal, color = "BUY PE (STRONG BEARISH)", "#FF3D00"
    elif inst_score <= 45:
        signal, color = "BUY PE (BEARISH LEAN)", "#FF3D00"
    else:
        signal, color = "WAIT / HEDGE (RANGE BOUND)", "#FFC107"

    if inst_score > 50:
        entry = ltp
        t1, t2, t3 = ltp + (em*0.5), ltp + em, ltp + (em*1.5)
        sl = ltp - (em*0.4)
    else:
        entry = ltp
        t1, t2, t3 = ltp - (em*0.5), ltp - em, ltp - (em*1.5)
        sl = ltp + (em*0.4)

    rr = f"1 : {abs((t2 - entry) / (entry - sl)):.1f}" if entry != sl else "N/A"

    return {
        "score": inst_score, "bull_prob": int(bull_prob), "bear_prob": int(bear_prob), 
        "side_prob": int(side_prob), "confidence": confidence, "reasons": reasons,
        "signal": signal, "color": color,
        "entry": entry, "t1": t1, "t2": t2, "t3": t3, "sl": sl, "rr": rr
    }
