import time
import pandas as pd
import dhanhq
import inspect
from pprint import pformat
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
                
                # --- FULL RAW JSON INSPECTION ---
                logger.info("========== FULL DHAN API RESPONSE ==========")
                logger.info(pformat(response))
                logger.info("============================================")
                logger.info(f"Expiry Used: {expiry_date}")
                
                if not response or response.get("status") != "success":
                    logger.error(f"Option Chain API Failed. Response: {response}")
                    time.sleep(2 ** attempt)
                    continue
                
                data = response.get("data")
                if isinstance(data, dict):
                    logger.info(f"Data Keys: {list(data.keys())}")
                
                ltp = response.get("last_price", data.get("last_price", 0) if isinstance(data, dict) else 0)
                return ltp, response
                
            except Exception:
                logger.exception("CRITICAL: option_chain call raised an exception")
            
            time.sleep(2 ** attempt)
            
        return None, None

    def process_oc_to_dataframe(self, response):
        """
        Generalized Normalization Engine: 
        Safely unpacks any response layout and maps alternate schema names to standard columns.
        """
        if not response:
            return pd.DataFrame()

        payload = response
        if isinstance(response, dict):
            payload = response.get("data", response)
            if isinstance(payload, dict):
                if "oc" in payload:
                    payload = payload["oc"]
                elif "records" in payload:
                    payload = payload["records"]
                elif "optionChain" in payload:
                    payload = payload["optionChain"]

        rows = []

        if isinstance(payload, dict):
            for strike_key, val in payload.items():
                if strike_key in ["last_price", "spot_price", "ltp"] or not isinstance(val, dict):
                    continue
                try:
                    strike_val = float(strike_key)
                except ValueError:
                    continue
                
                ce = val.get("ce", val.get("callOptions", val.get("CE", {})))
                pe = val.get("pe", val.get("putOptions", val.get("PE", {})))
                
                rows.append({
                    "Strike": strike_val,
                    "CE_OI": ce.get("oi", ce.get("open_interest", ce.get("openInterest", 0))),
                    "CE_LTP": ce.get("last_price", ce.get("ltp", ce.get("close", 0))),
                    "CE_IV": ce.get("implied_volatility", ce.get("iv", ce.get("impliedVolatility", 0))),
                    "CE_Delta": ce.get("greeks", {}).get("delta", ce.get("delta", 0)) if isinstance(ce.get("greeks"), dict) else ce.get("delta", 0),
                    "PE_OI": pe.get("oi", pe.get("open_interest", pe.get("openInterest", 0))),
                    "PE_LTP": pe.get("last_price", pe.get("ltp", pe.get("close", 0))),
                    "PE_IV": pe.get("implied_volatility", pe.get("iv", pe.get("impliedVolatility", 0))),
                    "PE_Delta": pe.get("greeks", {}).get("delta", pe.get("delta", 0)) if isinstance(pe.get("greeks"), dict) else pe.get("delta", 0)
                })

        elif isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                strike_val = float(item.get("strike_price", item.get("strikePrice", item.get("Strike", 0))))
                ce = item.get("ce", item.get("callOptions", item.get("CE", {})))
                pe = item.get("pe", item.get("putOptions", item.get("PE", {})))
                
                rows.append({
                    "Strike": strike_val,
                    "CE_OI": ce.get("oi", ce.get("open_interest", ce.get("openInterest", 0))),
                    "CE_LTP": ce.get("last_price", ce.get("ltp", ce.get("close", 0))),
                    "CE_IV": ce.get("implied_volatility", ce.get("iv", ce.get("impliedVolatility", 0))),
                    "CE_Delta": ce.get("greeks", {}).get("delta", ce.get("delta", 0)) if isinstance(ce.get("greeks"), dict) else ce.get("delta", 0),
                    "PE_OI": pe.get("oi", pe.get("open_interest", pe.get("openInterest", 0))),
                    "PE_LTP": pe.get("last_price", pe.get("ltp", pe.get("close", 0))),
                    "PE_IV": pe.get("implied_volatility", pe.get("iv", pe.get("impliedVolatility", 0))),
                    "PE_Delta": pe.get("greeks", {}).get("delta", pe.get("delta", 0)) if isinstance(pe.get("greeks"), dict) else pe.get("delta", 0)
                })

        df = pd.DataFrame(rows)
        
        if df.empty:
            logger.error("Normalization produced an empty DataFrame. Check raw response logs above.")
            return pd.DataFrame()
            
        logger.info(f"Successfully normalized columns: {df.columns.tolist()}")
        return df.sort_values(by="Strike").reset_index(drop=True)
