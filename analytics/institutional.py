import pandas as pd

def calculate_exposures(df, ltp, lot_size=25):
    """
    SPRINT 5: Dealer Positioning & Walls
    Calculates Net GEX/DEX, and pinpoints exact Institutional Resistance/Support Walls.
    """
    df['CE_Gamma'] = pd.to_numeric(df['CE_Gamma'], errors='coerce').fillna(0)
    df['PE_Gamma'] = pd.to_numeric(df['PE_Gamma'], errors='coerce').fillna(0)
    df['CE_Delta'] = pd.to_numeric(df['CE_Delta'], errors='coerce').fillna(0)
    df['PE_Delta'] = pd.to_numeric(df['PE_Delta'], errors='coerce').fillna(0)
    
    # Exposure Math
    df['CE_GEX'] = df['CE_Gamma'] * df['CE_OI'] * lot_size * ltp * 0.01
    df['PE_GEX'] = df['PE_Gamma'] * df['PE_OI'] * lot_size * ltp * 0.01 * -1 
    df['CE_DEX'] = df['CE_Delta'] * df['CE_OI'] * lot_size * ltp
    df['PE_DEX'] = df['PE_Delta'] * df['PE_OI'] * lot_size * ltp * -1

    net_gex = df['CE_GEX'].sum() + df['PE_GEX'].sum()
    net_dex = df['CE_DEX'].sum() + df['PE_DEX'].sum()

    df['Net_Strike_GEX'] = df['CE_GEX'] + df['PE_GEX']
    gamma_flip = df.loc[df['Net_Strike_GEX'].abs().idxmin(), 'Strike'] if not df.empty else 0

    # SPRINT 5: Calculate Institutional Walls
    gamma_wall = df.loc[df['CE_GEX'].idxmax(), 'Strike'] if not df.empty else 0
    put_wall = df.loc[df['PE_GEX'].idxmin(), 'Strike'] if not df.empty else 0
    delta_wall = df.loc[df['CE_DEX'].idxmax(), 'Strike'] if not df.empty else 0

    return {
        "net_gex": net_gex,
        "net_dex": net_dex,
        "gamma_flip": gamma_flip,
        "gamma_wall": gamma_wall,
        "put_wall": put_wall,
        "delta_wall": delta_wall,
        "dealer_regime": "Long Gamma" if net_gex > 0 else "Short Gamma",
        "hedging_pressure": "Bullish" if net_dex < 0 else "Bearish"
    }
