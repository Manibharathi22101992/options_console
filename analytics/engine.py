import pandas as pd
import numpy as np

def calculate_pcr(df: pd.DataFrame):
    total_ce_oi = df["CE_OI"].sum()
    total_pe_oi = df["PE_OI"].sum()
    return round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 1.0

def calculate_max_pain(df: pd.DataFrame):
    if df.empty: return 0
    strikes = df["Strike"].values
    losses = []
    for spot in strikes:
        ce_loss = np.maximum(0, spot - df["Strike"]) * df["CE_OI"]
        pe_loss = np.maximum(0, df["Strike"] - spot) * df["PE_OI"]
        losses.append(np.sum(ce_loss + pe_loss))
    return strikes[np.argmin(losses)]
