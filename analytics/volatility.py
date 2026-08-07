import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

def analyze_volatility(df, ltp, baseline_ltp, expiry_date_str):
    """
    SPRINT 8: Expected Move Engine
    Anchors the Expected Move to the baseline and calculates position exhaustion.
    """
    try:
        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        dte = max(1, (expiry_date - today).days)
    except Exception:
        dte = 1
        
    df['strike_dist'] = (df['Strike'] - ltp).abs()
    if df.empty:
        return {"atm_iv": 0, "expected_move": 0, "lower_bound": 0, "upper_bound": 0, "position_pct": 50, "regime": "Unknown", "color": "#888"}
        
    atm_row = df.loc[df['strike_dist'].idxmin()]
    ce_iv = float(atm_row.get('CE_IV', 0))
    pe_iv = float(atm_row.get('PE_IV', 0))
    atm_iv = (ce_iv + pe_iv) / 2 if (ce_iv > 0 and pe_iv > 0) else max(ce_iv, pe_iv)
    
    iv_decimal = atm_iv / 100 if atm_iv > 1 else atm_iv
    atm_iv_display = atm_iv if atm_iv > 1 else atm_iv * 100
    
    # SPRINT 8: Anchored Expected Move Math
    expected_move = baseline_ltp * iv_decimal * np.sqrt(dte / 365)
    lower_bound = baseline_ltp - expected_move
    upper_bound = baseline_ltp + expected_move
    
    # Where are we inside the expected move?
    total_range = upper_bound - lower_bound
    if total_range > 0:
        position_pct = ((ltp - lower_bound) / total_range) * 100
    else:
        position_pct = 50.0
        
    # Cap between 0 and 100 for the UI progress bar
    position_pct = max(0, min(100, position_pct))
    
    if atm_iv_display > 22:
        regime, crush_risk, color = "High Volatility", "HIGH", "#FF3D00"
    elif atm_iv_display > 14:
        regime, crush_risk, color = "Elevated", "MODERATE", "#FFC107"
    else:
        regime, crush_risk, color = "Low Volatility", "LOW", "#00E676"
        
    return {
        "atm_iv": atm_iv_display,
        "expected_move": expected_move,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "position_pct": position_pct,
        "dte": dte,
        "regime": regime,
        "crush_risk": crush_risk,
        "color": color
    }
