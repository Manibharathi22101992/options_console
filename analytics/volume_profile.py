import pandas as pd
from typing import Dict, Any, Optional

_PREV_POC: Optional[float] = None

def calculate_volume_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculates POC, VAH, VAL and monitors POC shifting."""
    global _PREV_POC
    if df.empty or 'CE_Volume' not in df.columns:
        return {"poc": 0.0, "vah": 0.0, "val": 0.0, "poc_shift": "Stable"}

    df['Total_Vol'] = pd.to_numeric(df['CE_Volume'], errors='coerce').fillna(0) + \
                      pd.to_numeric(df['PE_Volume'], errors='coerce').fillna(0)
    
    total_vol = float(df['Total_Vol'].sum())
    if total_vol == 0:
        return {"poc": 0.0, "vah": 0.0, "val": 0.0, "poc_shift": "Stable"}

    poc_idx = df['Total_Vol'].idxmax()
    poc = float(df.loc[poc_idx, 'Strike'])

    # Shift tracking
    shift_dir = "Stable"
    if _PREV_POC is not None:
        if poc > _PREV_POC: shift_dir = "Shifting Up ↗"
        elif poc < _PREV_POC: shift_dir = "Shifting Down ↘"
    _PREV_POC = poc

    # Value Area (70%)
    target_vol = total_vol * 0.70
    sorted_df = df.sort_values(by='Total_Vol', ascending=False)
    
    cumulative_vol = 0.0
    va_strikes = []
    
    for _, row in sorted_df.iterrows():
        cumulative_vol += row['Total_Vol']
        va_strikes.append(row['Strike'])
        if cumulative_vol >= target_vol:
            break
            
    vah = float(max(va_strikes)) if va_strikes else poc
    val = float(min(va_strikes)) if va_strikes else poc

    return {
        "poc": poc,
        "vah": vah,
        "val": val,
        "poc_shift": shift_dir
    }
