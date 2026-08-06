import pandas as pd
import numpy as np

def calculate_pcr(df: pd.DataFrame):
    """Standard Overall PCR for backward compatibility"""
    if df.empty or "CE_OI" not in df.columns or "PE_OI" not in df.columns:
        return 1.0
    total_ce_oi = df["CE_OI"].sum()
    total_pe_oi = df["PE_OI"].sum()
    return round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0

def calculate_advanced_pcr(df: pd.DataFrame, ltp: float):
    """Calculates both Overall PCR and 5-Strike ATM PCR"""
    if df.empty or "CE_OI" not in df.columns or "PE_OI" not in df.columns or df["CE_OI"].sum() == 0:
        return 1.0, 1.0
        
    # 1. Overall PCR
    overall_pcr = round(df["PE_OI"].sum() / df["CE_OI"].sum(), 2)
    
    # 2. ATM PCR (Closest 5 strikes)
    if "Strike" in df.columns and ltp > 0:
        atm_df = df.iloc[(df['Strike'] - ltp).abs().argsort()[:5]]
        atm_ce_oi = atm_df["CE_OI"].sum()
        atm_pcr = round(atm_df["PE_OI"].sum() / atm_ce_oi, 2) if atm_ce_oi > 0 else 1.0
    else:
        atm_pcr = overall_pcr
    
    return overall_pcr, atm_pcr

def calculate_max_pain(df: pd.DataFrame):
    """Optimized Vectorized Max Pain Calculation"""
    if df.empty or "Strike" not in df.columns or "CE_OI" not in df.columns or "PE_OI" not in df.columns:
        return 0
    
    strikes = df["Strike"].values
    ce_oi = df["CE_OI"].values
    pe_oi = df["PE_OI"].values
    
    if len(strikes) == 0:
        return 0
    
    # Vectorized calculation to avoid slow O(n^2) loops
    spot_grid, strike_grid = np.meshgrid(strikes, strikes, indexing='ij')
    
    ce_loss = np.maximum(0, spot_grid - strike_grid) * ce_oi
    pe_loss = np.maximum(0, strike_grid - spot_grid) * pe_oi
    
    total_loss = np.sum(ce_loss + pe_loss, axis=1)
    
    return strikes[np.argmin(total_loss)]
