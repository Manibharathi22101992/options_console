import time
import json
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

def extract_option_chain(response):
    """Recursively/iteratively walks down JSON nodes to find the option chain container."""
    node = response
    while isinstance(node, dict):
        if "oc" in node:
            return node["oc"]
        if "records" in node:
            return node["records"]
        if "optionChain" in node:
            return node["optionChain"]
        if "data" in node:
            node = node["data"]
            continue
        break
    return {}

def extract_last_price(response):
    """Safely extracts spot / last traded price from any nesting level."""
    node = response
    while isinstance(node, dict):
        for key in ["last_price", "ltp", "spot_price"]:
            if key in node:
                try:
                    return float(node[key])
                except (ValueError, TypeError):
                    pass
        if "data" in node:
            node = node["data"]
            continue
        break
    return 0.0

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
                
                if not response or response.get("status") != "success":
                    logger.error(f"Option Chain API Failed. Response: {response}")
                    time.sleep(2 ** attempt)
                    continue
                
                ltp = extract_last_price(response)
                return ltp, response
                
            except Exception:
                logger.exception("CRITICAL: option_chain call raised an exception")
            
            time.sleep(2 ** attempt)
            
        return None, None

    def process_oc_to_dataframe(self, response):
        """
        Extracts and normalizes the option chain data into a clean pandas DataFrame.
        """
        payload = extract_option_chain(response)
        
        if not payload or not isinstance(payload, dict):
            logger.error("Failed to extract valid option chain payload from response hierarchy.")
            return pd.DataFrame()

        rows = []
        for strike_key, val in payload.items():
            if strike_key in ["last_price", "spot_price", "ltp", "expiry"] or not isinstance(val, dict):
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

        df = pd.DataFrame(rows)
        
        if df.empty:
            logger.error("Extracted payload contained no valid strike rows.")
            return pd.DataFrame()
            
        logger.info(f"Successfully processed {len(df)} strike rows.")
        return df.sort_values(by="Strike").reset_index(drop=True)
