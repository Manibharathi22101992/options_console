import yaml
import os
from typing import Dict, Any

def load_weights() -> Dict[str, Any]:
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base_dir, 'config', 'weights.yaml'), 'r') as f:
            return yaml.safe_load(f)
    except Exception:
        return {"weights": {"flow": 0.35, "gamma": 0.20, "delta": 0.20, "pcr": 0.15, "vwap_proxy": 0.10}}

def generate_institutional_decision(
    ltp: float,
    baselines: Dict[str, float],
    pcr_score: float,
    net_gex: float,
    net_dex: float,
    expected_move: float,
    flow_score: float
) -> Dict[str, Any]:
    """
    Calculates weighted Institutional Score and returns exact point contributions
    for each analytical factor.
    """
    cfg = load_weights()
    w = cfg['weights']

    # Raw factor evaluations (0-100)
    gex_val = 80.0 if net_gex < 0 else 40.0
    dex_val = 80.0 if net_dex < 0 else 40.0
    vwap_val = 90.0 if ltp > baselines.get('vwap', ltp) else 20.0

    # Calculate weighted contributions
    contrib_flow = float(flow_score * w['flow'])
    contrib_gamma = float(gex_val * w['gamma'])
    contrib_delta = float(dex_val * w['delta'])
    contrib_pcr = float(pcr_score * w['pcr'])
    contrib_vwap = float(vwap_val * w['vwap_proxy'])

    inst_score = int(contrib_flow + contrib_gamma + contrib_delta + contrib_pcr + contrib_vwap)

    # Probabilities
    side_prob = 15.0 if net_gex < 0 else 40.0
    rem = 100.0 - side_prob
    bull_prob = rem * (inst_score / 100.0)
    bear_prob = rem - bull_prob
    confidence = int(abs(bull_prob - bear_prob))

    # Signal & Planning
    em = expected_move if expected_move > 20 else 50.0
    if inst_score >= 60:
        signal, color = "BUY CE (STRONG BULLISH)", "#00E676"
        entry = ltp
        t1, t2, t3 = ltp + (em*0.5), ltp + em, ltp + (em*1.5)
        sl = ltp - (em*0.4)
    elif inst_score <= 40:
        signal, color = "BUY PE (STRONG BEARISH)", "#FF3D00"
        entry = ltp
        t1, t2, t3 = ltp - (em*0.5), ltp - em, ltp - (em*1.5)
        sl = ltp + (em*0.4)
    else:
        signal, color = "WAIT / RANGE BOUND", "#FFC107"
        entry = ltp
        t1, t2, t3 = ltp + em, ltp + (em*1.5), ltp + (em*2)
        sl = ltp - em

    rr = f"1 : {abs((t2 - entry) / (entry - sl)):.1f}" if entry != sl else "N/A"

    contributions = {
        "Flow": round(contrib_flow, 1),
        "Gamma": round(contrib_gamma, 1),
        "Delta": round(contrib_delta, 1),
        "PCR": round(contrib_pcr, 1),
        "VWAP": round(contrib_vwap, 1)
    }

    return {
        "score": inst_score,
        "bull_prob": int(bull_prob),
        "bear_prob": int(bear_prob),
        "side_prob": int(side_prob),
        "confidence": confidence,
        "signal": signal,
        "color": color,
        "entry": entry,
        "t1": t1, "t2": t2, "t3": t3, "sl": sl,
        "rr": rr,
        "contributions": contributions
    }
