def analyze_market(ltp, df, max_pain):
    pcr = sum(df["PE_OI"]) / sum(df["CE_OI"]) if sum(df["CE_OI"]) > 0 else 1
    
    regime = "Bullish" if ltp > max_pain else ("Bearish" if ltp < max_pain else "Ranging")
    
    score = 50
    if pcr > 1.2: score += 20
    elif pcr < 0.8: score -= 20
    
    if regime == "Bullish": score += 15
    elif regime == "Bearish": score -= 15
    
    avg_ce_iv = df["CE_IV"].mean()
    avg_pe_iv = df["PE_IV"].mean()
    if avg_ce_iv > avg_pe_iv: score += 15
    else: score -= 15
        
    score = max(0, min(100, score))
    confidence = abs(score - 50) * 2 
    
    if score >= 70:
        rec, reason = "BUY CE", f"High PCR ({pcr:.2f}) and Bullish Regime."
    elif score <= 30:
        rec, reason = "BUY PE", f"Low PCR ({pcr:.2f}) and Bearish Regime."
    else:
        rec, reason = "WAIT", "Conflicting signals. Market in consolidation."
        
    return {
        "regime": regime,
        "confluence": score,
        "confidence": confidence,
        "recommendation": rec,
        "reason": reason
    }
