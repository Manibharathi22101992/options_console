from dhanhq import DhanContext, dhanhq
from core.config import CLIENT_ID, ACCESS_TOKEN, NIFTY_ID, EXPIRY_DATE, logger
import pandas as pd

class DhanMarketData:
    def __init__(self):
        try:
            # NEW v2.x LOGIN METHOD:
            dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
            self.dhan = dhanhq(dhan_context)
            logger.info("Dhan API Initialized.")
        except Exception as e:
            logger.error(f"Dhan API Auth Failed: {e}")

    def get_live_option_chain(self):
        try:
            response = self.dhan.get_option_chain(
                underlying_security_id=NIFTY_ID,
                underlying_type="INDEX",
                expiry_date=EXPIRY_DATE
            )
            
            if "data" not in response:
                return None, None
            
            ltp = response["data"].get("last_price", 0)
            oc_data = response["data"].get("oc", {})
            return ltp, oc_data
        except Exception as e:
            logger.error(f"Error fetching Option Chain: {e}")
            return None, None

    def process_oc_to_dataframe(self, oc_data):
        rows = []
        for strike, data in oc_data.items():
            strike_price = float(strike)
            ce = data.get("ce", {})
            pe = data.get("pe", {})
            
            rows.append({
                "Strike": strike_price,
                "CE_OI": ce.get("open_interest", 0),
                "CE_LTP": ce.get("last_price", 0),
                "CE_IV": ce.get("implied_volatility", 0),
                "CE_Delta": ce.get("greeks", {}).get("delta", 0),
                "PE_OI": pe.get("open_interest", 0),
                "PE_LTP": pe.get("last_price", 0),
                "PE_IV": pe.get("implied_volatility", 0),
                "PE_Delta": pe.get("greeks", {}).get("delta", 0)
            })
        return pd.DataFrame(rows).sort_values("Strike").reset_index(drop=True)
