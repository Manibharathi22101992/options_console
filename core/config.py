import logging
import streamlit as st

# Read credentials from Streamlit Secrets (Cloud Deployment)
CLIENT_ID = st.secrets["DHAN_CLIENT_ID"]
ACCESS_TOKEN = st.secrets["DHAN_ACCESS_TOKEN"]
NIFTY_ID = st.secrets.get("NIFTY_SECURITY_ID", "13")
EXPIRY_DATE = st.secrets["EXPIRY_DATE"]

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NiftyOptionsDash")
