import sqlite3
from typing import Dict, Any, List
import pandas as pd
import time

def init_feature_store() -> None:
    """Initializes the SQLite feature store for rolling calculations."""
    conn = sqlite3.connect('quant_engine.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feature_store (
            timestamp REAL,
            spot REAL,
            pcr REAL,
            total_oi REAL,
            net_gex REAL,
            net_dex REAL,
            iv REAL,
            volume REAL
        )
    ''')
    conn.commit()
    conn.close()

def log_snapshot(spot: float, pcr: float, total_oi: float, net_gex: float, net_dex: float, iv: float, volume: float) -> None:
    """Logs a live market snapshot for time-series feature calculation."""
    conn = sqlite3.connect('quant_engine.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO feature_store VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (time.time(), spot, pcr, total_oi, net_gex, net_dex, iv, volume)
    )
    conn.commit()
    conn.close()

def compute_features() -> Dict[str, Any]:
    """Computes velocity, momentum, and acceleration across rolling windows."""
    conn = sqlite3.connect('quant_engine.db')
    df = pd.read_sql("SELECT * FROM feature_store ORDER BY timestamp DESC LIMIT 60", conn)
    conn.close()

    if len(df) < 2:
        return {
            "spot_velocity": 0.0, "pcr_momentum": 0.0, "oi_acceleration": 0.0,
            "iv_velocity": 0.0, "volume_velocity": 0.0, "premium_expansion": 0.0
        }

    # Velocity (Delta between last 2 ticks)
    spot_vel = float(df['spot'].iloc[0] - df['spot'].iloc[1])
    pcr_mom = float(df['pcr'].iloc[0] - df['pcr'].iloc[-min(5, len(df))])
    iv_vel = float(df['iv'].iloc[0] - df['iv'].iloc[1])
    vol_vel = float(df['volume'].iloc[0] - df['volume'].iloc[1])
    
    # Acceleration (Change in velocity)
    if len(df) >= 3:
        vel_1 = df['total_oi'].iloc[0] - df['total_oi'].iloc[1]
        vel_2 = df['total_oi'].iloc[1] - df['total_oi'].iloc[2]
        oi_accel = float(vel_1 - vel_2)
    else:
        oi_accel = 0.0

    premium_expansion = float(iv_vel * spot_vel)

    return {
        "spot_velocity": spot_vel,
        "pcr_momentum": pcr_mom,
        "oi_acceleration": oi_accel,
        "iv_velocity": iv_vel,
        "volume_velocity": vol_vel,
        "premium_expansion": premium_expansion
    }
