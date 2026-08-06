from dhanhq import DhanContext, dhanhq
from core.config import CLIENT_ID, ACCESS_TOKEN, NIFTY_ID, EXPIRY_DATE, logger
import pandas as pd

class DhanMarketData:
    def __init__(self):
        try:
            dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
            self.dhan = dhanhq(dhan_context)
            logger.info("Dhan API Initialized.")
        except Exception as e:
            logger.error(f"Dhan API Auth Failed: {e}")

    def get_live_option_chain(self):
        try:
            # v2.x API Fix: Method is 'option_chain', not 'get_option_chain'
            # Arguments: Security ID, Exchange Segment ("IDX_I" for Index), Expiry Date
            response = self.dhan.option_chain(
                NIFTY_ID,
                "IDX_I", 
                EXPIRY_DATE
            )
            
            if not response or response.get("status") == "failure" or "data" not in response:
                logger.error(f"API Returned Failure: {response}")
                return None, None
            
            data = response.get("data", {})
            oc_data = data.get("oc", data) if isinstance(data, dict) else data
            
            # Extract Spot Price if provided
            ltp = response.get("last_price", data.get("last_price", 0))
            
            return ltp, oc_data
        except Exception as e:
            logger.error(f"Error fetching Option Chain: {e}")
            return None, None

    def process_oc_to_dataframe(self, oc_data):
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
                # v2 API uses 'oi' instead of 'open_interest'
                "CE_OI": ce.get("oi", ce.get("open_interest", 0)),
                "CE_LTP": ce.get("last_price", 0),
                "CE_IV": ce.get("implied_volatility", 0),
                "CE_Delta": ce.get("greeks", {}).get("delta", 0) if isinstance(ce.get("greeks"), dict) else 0,
                "PE_OI": pe.get("oi", pe.get("open_interest", 0)),
                "PE_LTP": pe.get("last_price", 0),
                "PE_IV": pe.get("implied_volatility", 0),
                "PE_Delta": pe.get("greeks", {}).get("delta", 0) if isinstance(pe.get("greeks"), dict) else 0
            })
        return pd.DataFrame(rows).sort_values("Strike").reset_index(drop=True)
