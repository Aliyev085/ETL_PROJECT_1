#!/usr/bin/env python3
# -- coding: utf-8 --
"""
Bina.az Apartments ETL (cards-only)

Modes:
  --verify-only   : check if main page is reachable and has listing cards
  --initial       : scrape latest N (env: BINA_MAX_LISTINGS_INITIAL) and insert new rows only
  --incremental   : for cron; scrape ~M (env: BINA_MAX_LISTINGS_INCREMENTAL) and insert new rows only

Notes:
  * No per-listing page opens (fast).
  * No DDL here; run schema.sql manually once.
  * One DB connection per run; new cursor per query.
  * posted_at saved as naive UTC (TIMESTAMP WITHOUT TIME ZONE).
"""

import argparse
import time
from pathlib import Path
from bina.config import settings
from bina.db import DBClient
from bina.scraper import SeleniumDriver
from bina.pipeline import Pipeline
from bina.rabbit import RabbitMQ

HEARTBEAT_PATH = "/opt/airflow/tmp/etl_heartbeat"


def write_heartbeat(status: str = "success") -> None:
    """Write or refresh the ETL heartbeat file with a timestamp and status."""
    try:
        Path(HEARTBEAT_PATH).write_text(
            f"{status} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        print(f"[heartbeat] {status} -> {HEARTBEAT_PATH}")
    except Exception as e:
        print(f"[WARN] Failed to write heartbeat: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bina.az apartments ETL (cards-only)")
    parser.add_argument("--verify-only", action="store_true", help="Check reachability only")
    parser.add_argument("--initial", action="store_true", help="Run initial load")
    parser.add_argument("--incremental", action="store_true", help="Run incremental update")
    args = parser.parse_args()

    if not (args.verify_only or args.initial or args.incremental):
        parser.error("Choose one: --verify-only OR --initial OR --incremental")

    db = DBClient()
    browser = SeleniumDriver()
    pipe = Pipeline(db, browser)
    rabbit = RabbitMQ()

    mode = (
        "verify"
        if args.verify_only
        else "initial" if args.initial else "incremental"
    )

    print(f"[run] Starting ETL in {mode} mode...")
    write_heartbeat(f"{mode}_started")

    try:
        browser.get(settings.BINA_BASE_URL)

        if args.verify_only:
            ok = pipe.verify()
            print(f"[verify] Access OK: {ok}")
            write_heartbeat("verify_ok" if ok else "verify_fail")
            return

        max_new = (
            settings.MAX_LISTINGS_INITIAL
            if args.initial
            else settings.MAX_LISTINGS_INCREMENTAL
        )

        new_listings = pipe.run(max_new=max_new)

        if new_listings:
            for item in new_listings:
                payload = {"listing_id": item["id"], "url": item["url"]}
                rabbit.publish(payload)
                print(f"[x] Published listing_id={item['id']} to queue {settings.RABBIT_QUEUE}")
            print(f"[{mode}] Inserted new rows: {len(new_listings)}")
            write_heartbeat(f"{mode}_success")
        else:
            print(f"[{mode}] No new listings found.")
            write_heartbeat(f"{mode}_no_new")

    except Exception as e:
        print(f"[ERROR] ETL failed: {e}")
        write_heartbeat("failed")
        raise

    finally:
        for name, obj in {"rabbit": rabbit, "browser": browser, "db": db}.items():
            try:
                obj.close()
            except Exception as e:
                print(f"[WARN] Failed to close {name}: {e}")
        print("[run] ETL completed. Resources closed.")


if __name__ == "__main__":
    main()
