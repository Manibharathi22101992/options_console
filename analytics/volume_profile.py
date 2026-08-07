import pandas as pd

def calculate_volume_profile(df):
    """
    SPRINT 6: Options Volume Profile Engine
    Calculates Point of Control (POC) and Value Area (VAH / VAL) representing 70% of total volume.
    """
    if df.empty or 'CE_Volume' not in df.columns:
        return {"poc": 0, "vah": 0, "val": 0, "total_vol": 0}

    # Aggregate total volume per strike
    df['Total_Vol'] = pd.to_numeric(df['CE_Volume'], errors='coerce').fillna(0) + \
                      pd.to_numeric(df['PE_Volume'], errors='coerce').fillna(0)
    
    total_vol = df['Total_Vol'].sum()
    if total_vol == 0:
        return {"poc": 0, "vah": 0, "val": 0, "total_vol": 0}

    # Point of Control (Highest Volume Node)
    poc_idx = df['Total_Vol'].idxmax()
    poc = df.loc[poc_idx, 'Strike']

    # Value Area calculation (Targeting 70% of total volume)
    target_vol = total_vol * 0.70
    sorted_df = df.sort_values(by='Total_Vol', ascending=False)
    
    cumulative_vol = 0
    value_area_strikes = []
    
    for _, row in sorted_df.iterrows():
        cumulative_vol += row['Total_Vol']
        value_area_strikes.append(row['Strike'])
        if cumulative_vol >= target_vol:
            break
            
    vah = max(value_area_strikes) if value_area_strikes else poc
    val = min(value_area_strikes) if value_area_strikes else poc

    return {
        "poc": poc,
        "vah": vah,
        "val": val,
        "total_vol": total_vol
    }
