import os
import logging

try:
    import streamlit as st
    CLIENT_ID = st.secrets.get("DHAN_CLIENT_ID", os.getenv("DHAN_CLIENT_ID"))
    ACCESS_TOKEN = st.secrets.get("DHAN_ACCESS_TOKEN", os.getenv("DHAN_ACCESS_TOKEN"))
except ImportError:
    CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
    ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

# --- STRICT VALIDATION ---
if not CLIENT_ID:
    raise RuntimeError("CRITICAL ERROR: DHAN_CLIENT_ID is missing from Configuration or Secrets.")
if not ACCESS_TOKEN:
    raise RuntimeError("CRITICAL ERROR: DHAN_ACCESS_TOKEN is missing from Configuration or Secrets.")

NIFTY_ID = "13"

# Advanced Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("QuantEngine")
