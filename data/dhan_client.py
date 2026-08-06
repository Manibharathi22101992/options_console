import time
import pandas as pd
import dhanhq
import inspect
from dhanhq import dhanhq as DhanHQClient
from core.config import CLIENT_ID, ACCESS_TOKEN, logger

UNDERLYINGS = {
    "NIFTY": {"id": 13, "segment": "IDX_I"},
    "BANKNIFTY": {"id": 25, "segment": "IDX_I"},
    "FINNIFTY": {"id": 27, "segment": "IDX_I"}
}

class DhanMarketData:
    def __init__(self):
        self.diagnostic_printed = False
        try:
            logger.info(f"Dhan SDK version: {getattr(dhanhq, '__version__', 'unknown')}")
            
            try:
                from dhanhq import DhanContext
                dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
                self.dhan = DhanHQClient(dhan_context)
            except ImportError:
                self.dhan = DhanHQClient(CLIENT_ID, ACCESS_TOKEN)

            auth_test = self.dhan.get_fund_limits()
            if isinstance(auth_test, dict) and auth_test.get("status") == "failure":
                logger.error(f"Auth test failed: {auth_test}")
        except Exception:
            logger.exception("Init Failure")

    def get_live_option_chain(self, expiry_date, symbol="NIFTY", retries=3):
        if not self.diagnostic_printed:
            try:
                logger.info(f"DEBUG: option_chain signature: {inspect.signature(self.dhan.option_chain)}")
            except Exception as e:
                logger.error(f"Could not inspect signature: {e}")
            self.diagnostic_printed = True

        cfg = UNDERLYINGS.get(symbol, UNDERLYINGS["NIFTY"])
        sec_id = cfg["id"]
        segment = cfg["segment"]
        
        logger.info(f"Request: id={sec_id}, segment={segment}, expiry={expiry_date}")
        
        for attempt in range(retries):
            try:
                response = self.dhan.option_chain(
                    under_security_id=sec_id,
                    under_exchange_segment=segment,
                    expiry=expiry_date
                )
                
                if response and response.get("status") != "failure" and "data" in response:
                    data = response.get("data", {})
                    ltp = response.get("last_price", data.get("last_price", 0))
                    oc_data = data.get("oc", data) if isinstance(data, dict) else data
                    return ltp, oc_data
                
                logger.error(f"Option Chain Failed. Response: {response}")
                
            except Exception:
                logger.exception("CRITICAL: option_chain() raised an exception")
            
            time.sleep(2 ** attempt)
            
        return None, None

    def process_oc_to_dataframe(self, oc_data):
        if not oc_data or not isinstance(oc_data, dict): 
            return pd.DataFrame()
        
        rows = []
        for strike, data in oc_data.items():
            if strike == "last_price" or not isinstance(data, dict): continue
            try:
                strike_price = float(strike)
            except ValueError: continue
                
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
            
        # GUARD: Prevent pandas sort crash if API returns an empty structure
        if not rows:
            return pd.DataFrame()
            
        df = pd.DataFrame(rows)
        required_cols = ["Strike", "CE_OI", "PE_OI", "CE_LTP", "PE_LTP"]
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"FATAL: Missing required column {col} in API response")
                return pd.DataFrame()
                
        return df.sort_values("Strike").reset_index(drop=True)
