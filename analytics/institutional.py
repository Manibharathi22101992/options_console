import pandas as pd

def calculate_exposures(df, ltp, lot_size=25):
    """
    Calculates Dealer Gamma Exposure (GEX) and Delta Exposure (DEX).
    Positive GEX = Market Makers suppress volatility (Range).
    Negative GEX = Market Makers amplify volatility (Trend).
    """
    # Normalize Greeks
    df['CE_Gamma'] = pd.to_numeric(df['CE_Gamma'], errors='coerce').fillna(0)
    df['PE_Gamma'] = pd.to_numeric(df['PE_Gamma'], errors='coerce').fillna(0)
    df['CE_Delta'] = pd.to_numeric(df['CE_Delta'], errors='coerce').fillna(0)
    df['PE_Delta'] = pd.to_numeric(df['PE_Delta'], errors='coerce').fillna(0)
    
    # Dealer Exposure Math (Assuming Dealers sell calls/puts to public)
    # GEX is multiplied by 100 for normalization, and spot price to get cash value.
    df['CE_GEX'] = df['CE_Gamma'] * df['CE_OI'] * lot_size * ltp * 0.01
    df['PE_GEX'] = df['PE_Gamma'] * df['PE_OI'] * lot_size * ltp * 0.01 * -1 # Puts have negative Gamma impact
    
    df['CE_DEX'] = df['CE_Delta'] * df['CE_OI'] * lot_size * ltp
    df['PE_DEX'] = df['PE_Delta'] * df['PE_OI'] * lot_size * ltp * -1

    total_ce_gex = df['CE_GEX'].sum()
    total_pe_gex = df['PE_GEX'].sum()
    net_gex = total_ce_gex + total_pe_gex  
    
    total_ce_dex = df['CE_DEX'].sum()
    total_pe_dex = df['PE_DEX'].sum()
    net_dex = total_ce_dex + total_pe_dex

    # Identify Gamma Flip Point (Strike with highest absolute Net GEX)
    df['Net_Strike_GEX'] = df['CE_GEX'] + df['PE_GEX']
    gamma_flip = df.loc[df['Net_Strike_GEX'].abs().idxmax(), 'Strike'] if not df.empty else 0

    return {
        "net_gex": net_gex,
        "net_dex": net_dex,
        "gamma_flip": gamma_flip,
        "dealer_regime": "Long Gamma (Mean Reverting / Low Volatility)" if net_gex > 0 else "Short Gamma (Trending / High Volatility)",
        "hedging_pressure": "Bullish (Dealers buying to hedge)" if net_dex < 0 else "Bearish (Dealers selling to hedge)"
    }
