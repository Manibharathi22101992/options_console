import time
import pandas as pd
from dhanhq import DhanContext, dhanhq
from core.config import CLIENT_ID, ACCESS_TOKEN, NIFTY_ID, logger

class DhanMarketData:
    def __init__(self):
        try:
            dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
            self.dhan = dhanhq(dhan_context)
            logger.info("Dhan API Initialized.")
        except Exception as e:
            logger.error(f"Dhan API Auth Failed: {e}")

    def get_live_option_chain(self, expiry_date, retries=3):
        """Fetches Option Chain with Exponential Backoff Retry Mechanism"""
        for attempt in range(retries):
            try:
                response = self.dhan.option_chain(NIFTY_ID, "IDX_I", expiry_date)
                
                if response and response.get("status") != "failure" and "data" in response:
                    data = response.get("data", {})
                    ltp = response.get("last_price", data.get("last_price", 0))
                    oc_data = data.get("oc", data) if isinstance(data, dict) else data
                    return ltp, oc_data
                    
                logger.warning(f"API Attempt {attempt+1} Failed: {response.get('remarks')}")
            except Exception as e:
                logger.error(f"Connection Error (Attempt {attempt+1}): {e}")
            
            # Exponential backoff: 1s, 2s, 4s...
            time.sleep(2 ** attempt)
            
        return None, None

    def process_oc_to_dataframe(self, oc_data):
        if not oc_data: return pd.DataFrame()
        
        rows = []
        for strike, data in oc_data.items():
            if strike == "last_price": continue
            try:
                strike_price = float(strike)
            except ValueError:
                continue
                
            ce = data.get("ce", {})
            pe = data.get("pe", {})
            
            rows.append({
                "Strike": strike_price,
                "CE_OI": ce.get("oi", ce.get("open_interest", 0)),
                "CE_LTP": ce.get("last_price", 0),
                "CE_IV": ce.get("implied_volatility", 0),
                "CE_Delta": ce.get("greeks", {}).get("delta", 0) if isinstance(ce.get("greeks"), dict) else 0,
                "PE_OI": pe.get("oi", pe.get("open_interest", 0)),
                "PE_LTP": pe.get("last_price", 0),
                "PE_IV": pe.get("implied_volatility", 0),
                "PE_Delta": pe.get("greeks", {}).get("delta", 0) if isinstance(pe.get("greeks"), dict) else 0
            })
            
        df = pd.DataFrame(rows)
        # DATA VALIDATION: Ensure critical columns exist before passing to engine
        required_cols = ["Strike", "CE_OI", "PE_OI", "CE_LTP", "PE_LTP"]
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"FATAL: Missing required column {col} in API response")
                return pd.DataFrame()
                
        return df.sort_values("Strike").reset_index(drop=True)
