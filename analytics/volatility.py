import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

def analyze_volatility(df, ltp, expiry_date_str):
    """
    Phase 6: Volatility Engine
    Calculates ATM IV, Expected Move bounds, and IV Crush Risk.
    """
    try:
        # Calculate Days to Expiry (DTE)
        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        dte = (expiry_date - today).days
        
        # 0 DTE options still have time value during the day; treat as 1 day for math
        if dte < 1: 
            dte = 1 
    except Exception:
        dte = 1
        
    # Find ATM strike
    df['strike_dist'] = (df['Strike'] - ltp).abs()
    if df.empty:
        return {"atm_iv": 0, "expected_move": 0, "regime": "Unknown", "crush_risk": "Unknown", "color": "#888"}
        
    atm_row = df.loc[df['strike_dist'].idxmin()]
    
    ce_iv = float(atm_row.get('CE_IV', 0))
    pe_iv = float(atm_row.get('PE_IV', 0))
    
    # Average the Call and Put IV for the ATM strike
    atm_iv = (ce_iv + pe_iv) / 2 if (ce_iv > 0 and pe_iv > 0) else max(ce_iv, pe_iv)
    
    # Standardize IV format (Dhan sometimes passes percentage as whole numbers)
    iv_decimal = atm_iv / 100 if atm_iv > 1 else atm_iv
    atm_iv_display = atm_iv if atm_iv > 1 else atm_iv * 100
    
    # Calculate Expected Move (± Points)
    expected_move = ltp * iv_decimal * np.sqrt(dte / 365)
    
    # Determine Volatility Regime & Crush Risk
    if atm_iv_display > 22:
        regime = "High Volatility (Seller Market)"
        crush_risk = "HIGH CRUSH RISK"
        color = "#FF3D00" # Red
    elif atm_iv_display > 14:
        regime = "Elevated (Neutral)"
        crush_risk = "MODERATE"
        color = "#FFC107" # Yellow
    else:
        regime = "Low Volatility (Buyer Market)"
        crush_risk = "LOW"
        color = "#00E676" # Green
        
    return {
        "atm_iv": atm_iv_display,
        "expected_move": expected_move,
        "dte": dte,
        "regime": regime,
        "crush_risk": crush_risk,
        "color": color
    }
