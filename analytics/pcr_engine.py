import numpy as np

def calculate_nonlinear_pcr_score(pcr: float) -> float:
    """
    Computes a non-linear PCR score (0-100).
    Flatter around neutral 1.0, highly sensitive at extremes (<0.7 or >1.3).
    """
    # Sigmoidal smooth mapping centered at 1.0
    # Scaled so extremes map towards 0 or 100 cleanly
    normalized = (pcr - 1.0) * 4.0
    score = 100 / (1.0 + np.exp(-normalized))
    return float(np.clip(score, 0.0, 100.0))
