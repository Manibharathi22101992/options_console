def analyze_market(ltp, df, max_pain, overall_pcr, atm_pcr):
    """
    Institutional Weighted Confluence Engine
    Evaluates multiple quantitative parameters to generate a confidence score.
    """
    reasons = []
    score = 0
    
    # 1. Market Regime Detection (Weight: 20%)
    if ltp > max_pain * 1.005:
        regime = "Trending Up"
        score += 20
        reasons.append("✓ Price holding above Max Pain (Trend Bullish)")
    elif ltp < max_pain * 0.995:
        regime = "Trending Down"
        score -= 20
        reasons.append("✗ Price trading below Max Pain (Trend Bearish)")
    else:
        regime = "Range Bound"
        reasons.append("- Price pinned near Max Pain (Consolidation)")

    # 2. Smart Money Divergence (ATM vs Overall PCR) (Weight: 25%)
    if atm_pcr > overall_pcr and atm_pcr > 1.0:
        score += 25
        reasons.append(f"✓ Smart Money buying ITM Puts/Selling ATM Calls (ATM PCR {atm_pcr} > Overall)")
    elif atm_pcr < overall_pcr and atm_pcr < 1.0:
        score -= 25
        reasons.append(f"✗ Aggressive Call Writing at ATM (ATM PCR {atm_pcr} < Overall)")
    else:
        reasons.append("- Neutral options flow")

    # 3. Absolute PCR Filter (Weight: 20%)
    if overall_pcr > 1.2:
        score += 20
        reasons.append("✓ Strong Put Support base (Overall PCR > 1.2)")
    elif overall_pcr < 0.8:
        score -= 20
        reasons.append("✗ Heavy Call Resistance overhead (Overall PCR < 0.8)")

    # 4. IV Skew & Premium Velocity (Weight: 15%)
    avg_ce_iv = df["CE_IV"].replace(0, 1).mean()
    avg_pe_iv = df["PE_IV"].replace(0, 1).mean()
    
    if avg_ce_iv > avg_pe_iv * 1.1:
        score += 15
        reasons.append("✓ Call IV Premium Expansion (Upside fear)")
    elif avg_pe_iv > avg_ce_iv * 1.1:
        score -= 15
        reasons.append("✗ Put IV Premium Expansion (Downside fear)")

    # 5. Normalization & Decision Generation
    # Convert arbitrary score (-80 to +80) to a 0-100 Confidence Index
    confidence_index = max(0, min(100, int(((score + 80) / 160) * 100)))
    
    if confidence_index >= 70:
        rec = "BUY CE / SELL PE"
        risk = "Medium" if confidence_index < 85 else "Low"
    elif confidence_index <= 30:
        rec = "BUY PE / SELL CE"
        risk = "Medium" if confidence_index > 15 else "Low"
    else:
        rec = "WAIT / HEDGE"
        risk = "High (Chop Zone)"
        reasons.append("! Conflicting metrics detected. Capital preservation mode.")

    return {
        "regime": regime,
        "confluence": confidence_index,
        "confidence": abs(confidence_index - 50) * 2, # 0-100% directional conviction
        "recommendation": rec,
        "reason": "<br>".join(reasons),
        "risk": risk
    }
