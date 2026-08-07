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

    def get_valid_expiries(self, symbol="NIFTY"):
        """Automatically fetches valid live expiries directly from Dhan exchange"""
        cfg = UNDERLYINGS.get(symbol, UNDERLYINGS["NIFTY"])
        try:
            # Try standard SDK method name
            if hasattr(self.dhan, "expiry_list"):
                resp = self.dhan.expiry_list(cfg["id"], cfg["segment"])
            elif hasattr(self.dhan, "get_expiry_list"):
                resp = self.dhan.get_expiry_list(underlying_security_id=str(cfg["id"]), underlying_type="INDEX")
            else:
                return []
                
            if resp and isinstance(resp, dict):
                data = resp.get("data", resp)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "expiry" in data:
                    return data["expiry"]
        except Exception:
            logger.exception("Failed to fetch exchange expiry list")
        return []

    def get_live_option_chain(self, expiry_date, symbol="NIFTY", retries=3):
        cfg = UNDERLYINGS.get(symbol, UNDERLYINGS["NIFTY"])
        sec_id = cfg["id"]
        segment = cfg["segment"]
        
        # Auto-correct expiry using exchange list if user date returns empty
        valid_expiries = self.get_valid_expiries(symbol)
        if valid_expiries and isinstance(valid_expiries, list):
            logger.info(f"Exchange active expiries available: {valid_expiries[:5]}")
            if expiry_date not in valid_expiries:
                # Auto-select the nearest active expiry
                nearest_expiry = valid_expiries[0]
                logger.warning(f"Provided expiry '{expiry_date}' not found in active exchange list. Auto-switching to nearest active expiry: {nearest_expiry}")
                expiry_date = nearest_expiry

        logger.info(f"Requesting Option Chain -> id={sec_id}, segment={segment}, expiry={expiry_date}")
        
        for attempt in range(retries):
            try:
                # Try option_chain or get_option_chain
                if hasattr(self.dhan, "option_chain"):
                    response = self.dhan.option_chain(
                        under_security_id=sec_id,
                        under_exchange_segment=segment,
                        expiry=expiry_date
                    )
                elif hasattr(self.dhan, "get_option_chain"):
                    response = self.dhan.get_option_chain(
                        underlying_security_id=str(sec_id),
                        underlying_type="INDEX",
                        expiry_date=expiry_date
                    )
                else:
                    logger.error("No option chain method found in SDK client.")
                    return None, None
                
                logger.info(f"Full Response Status: {response.get('status') if isinstance(response, dict) else 'Unknown'}")
                
                if not response or response.get("status") != "success":
                    logger.error(f"Option Chain API Failed. Response: {response}")
                    time.sleep(2 ** attempt)
                    continue
                
                data = response.get("data")
                if not data:
                    logger.error("API returned success but 'data' payload is empty.")
                    time.sleep(2 ** attempt)
                    continue
                
                if isinstance(data, dict):
                    oc_data = data.get("oc", data)
                elif isinstance(data, list):
                    oc_data = data
                else:
                    oc_data = {}

                ltp = response.get("last_price", data.get("last_price", 0) if isinstance(data, dict) else 0)
                return ltp, oc_data
                
            except Exception:
                logger.exception("CRITICAL: option_chain call raised an exception")
            
            time.sleep(2 ** attempt)
            
        return None, None

    def process_oc_to_dataframe(self, oc_data):
        if not oc_data: 
            return pd.DataFrame()
            
        rows = []
        if isinstance(oc_data, list):
            for item in oc_data:
                strike_price = float(item.get("strike_price", item.get("Strike", 0)))
                ce = item.get("ce", item.get("CE", {}))
                pe = item.get("pe", item.get("PE", {}))
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
        elif isinstance(oc_data, dict):
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
                
        df = pd.DataFrame(rows)
        if df.empty or "Strike" not in df.columns:
            logger.error("Option chain parsing produced an empty DataFrame or missing 'Strike' column.")
            return pd.DataFrame()
            
        return df.sort_values(by="Strike").reset_index(drop=True)
