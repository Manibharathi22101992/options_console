import time
import pandas as pd
import dhanhq
from dhanhq import dhanhq as DhanHQClient
from core.config import CLIENT_ID, ACCESS_TOKEN, NIFTY_ID, logger

class DhanMarketData:
    def __init__(self):
        try:
            logger.info(f"Dhan SDK version: {getattr(dhanhq, '__version__', 'unknown')}")
            
            # 1. Flexible SDK Initialization (Handles both v1 and v2 SDKs)
            try:
                from dhanhq import DhanContext
                dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
                self.dhan = DhanHQClient(dhan_context)
                logger.info("Initialized using DhanContext (v2+)")
            except ImportError:
                self.dhan = DhanHQClient(CLIENT_ID, ACCESS_TOKEN)
                logger.info("Initialized using standard args (v1.x)")

            # 2. Hard Authentication Test
            logger.info("Testing API Authentication with get_fund_limits()...")
            try:
                auth_test = self.dhan.get_fund_limits()
                if isinstance(auth_test, dict) and auth_test.get("status") == "failure":
                    logger.error("Authentication failed. Token may be expired or invalid.")
                    logger.error(f"Auth Response: {auth_test}")
                else:
                    logger.info("Authentication Successful.")
            except Exception:
                logger.exception("Auth Test Exception")

        except Exception:
            logger.exception("Dhan API Complete Init Failure")

    def get_live_option_chain(self, expiry_date, retries=3):
        logger.info(f"Requesting Option Chain. Expiry = {expiry_date}")
        
        for attempt in range(retries):
            try:
                response = self.dhan.option_chain(NIFTY_ID, "IDX_I", expiry_date)
                
                # Check for valid data
                if response and response.get("status") != "failure" and "data" in response and response.get("data"):
                    data = response.get("data", {})
                    ltp = response.get("last_price", data.get("last_price", 0))
                    oc_data = data.get("oc", data) if isinstance(data, dict) else data
                    return ltp, oc_data
                    
                # 3. Expose the hidden API response
                logger.warning(f"========== DHAN RESPONSE (Attempt {attempt+1}) ==========")
                logger.warning(f"Type: {type(response)}")
                logger.warning(response)
                logger.warning("=========================================================")
                
            except Exception:
                # 4. Include full traceback in logs
                logger.exception(f"Dhan API Exception (Attempt {attempt+1})")
            
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
        required_cols = ["Strike", "CE_OI", "PE_OI", "CE_LTP", "PE_LTP"]
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"FATAL: Missing required column {col} in API response")
                return pd.DataFrame()
                
        return df.sort_values("Strike").reset_index(drop=True)
