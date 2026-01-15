#!/usr/bin/env python3
import os
import time
import psutil
from flask import Flask, jsonify

# ========================
# CONFIGURATION
# ========================
ETL_CMD_MATCH = "main.py"               # your ETL script name
HEARTBEAT_PATH = "/tmp/etl_heartbeat"   # same path as in ETL
HEARTBEAT_MAX_AGE = 1200                # 20 minutes (match your cron frequency)

app = Flask(__name__)


# ========================
# PROCESS CHECK
# ========================
def etl_process_alive() -> bool:
    """Return True if any running process command line contains ETL_CMD_MATCH."""
    for proc in psutil.process_iter(attrs=["cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any(ETL_CMD_MATCH in part for part in cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception as e:
            print(f"[WARN] process check failed: {e}")
    return False


# ========================
# HEARTBEAT CHECK
# ========================
def etl_heartbeat_fresh(max_age_seconds: int = HEARTBEAT_MAX_AGE) -> bool:
    """Return True if the heartbeat file was updated recently."""
    try:
        mtime = os.path.getmtime(HEARTBEAT_PATH)
        age = time.time() - mtime
        return age <= max_age_seconds
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[WARN] heartbeat check failed: {e}")
        return False


# ========================
# FLASK ENDPOINT
# ========================
@app.route("/health")
def health():
    """
    Health endpoint for ETL service.

    Healthy if:
      - ETL process is alive, OR
      - Heartbeat file updated recently (indicating recent successful cycle)
    """
    alive = etl_process_alive()
    heartbeat = etl_heartbeat_fresh()
    healthy = heartbeat or alive  # for batch ETL, OR is correct

    response = {
        "etl_status": "up" if healthy else "down",
        "process_alive": alive,
        "heartbeat_fresh": heartbeat,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    return jsonify(response), (200 if healthy else 500)


# ========================
# ENTRY POINT
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5051)
