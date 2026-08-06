import pandas as pd
import numpy as np

def calculate_advanced_pcr(df: pd.DataFrame, ltp: float):
    """Calculates both Overall PCR and 5-Strike ATM PCR"""
    if df.empty or df["CE_OI"].sum() == 0:
        return 1.0, 1.0
        
    # 1. Overall PCR
    overall_pcr = round(df["PE_OI"].sum() / df["CE_OI"].sum(), 2)
    
    # 2. ATM PCR (Closest 5 strikes)
    atm_df = df.iloc[(df['Strike'] - ltp).abs().argsort()[:5]]
    atm_ce_oi = atm_df["CE_OI"].sum()
    atm_pcr = round(atm_df["PE_OI"].sum() / atm_ce_oi, 2) if atm_ce_oi > 0 else 1.0
    
    return overall_pcr, atm_pcr

def calculate_max_pain(df: pd.DataFrame):
    """Optimized Vectorized Max Pain Calculation"""
    if df.empty: return 0
    
    strikes = df["Strike"].values
    ce_oi = df["CE_OI"].values
    pe_oi = df["PE_OI"].values
    
    # Vectorized calculation to avoid slow O(n^2) loops
    spot_grid, strike_grid = np.meshgrid(strikes, strikes, indexing='ij')
    
    ce_loss = np.maximum(0, spot_grid - strike_grid) * ce_oi
    pe_loss = np.maximum(0, strike_grid - spot_grid) * pe_oi
    
    total_loss = np.sum(ce_loss + pe_loss, axis=1)
    
    return strikes[np.argmin(total_loss)]
