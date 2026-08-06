import sqlite3
import pandas as pd
from core.config import logger

DB_PATH = "nifty_dashboard.db"

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_signals (
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ltp REAL,
                    pcr REAL,
                    max_pain REAL,
                    regime TEXT,
                    confluence_score REAL,
                    recommendation TEXT
                )
            """)
            conn.commit()
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database Initialization Error: {e}")

def save_signal(data_dict):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.DataFrame([data_dict])
            df.to_sql("market_signals", conn, if_exists="append", index=False)
    except Exception as e:
        logger.error(f"Error saving signal: {e}")
