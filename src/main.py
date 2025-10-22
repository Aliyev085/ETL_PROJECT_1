#!/usr/bin/env python3
# -- coding: utf-8 --
"""
Bina.az apartments ETL (cards-only)

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

from bina.config import settings
from bina.db import DBClient
from bina.scraper import SeleniumDriver
from bina.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Bina.az apartments ETL (cards-only)")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--initial", action="store_true")
    parser.add_argument("--incremental", action="store_true")
    args = parser.parse_args()

    if not (args.verify_only or args.initial or args.incremental):
        parser.error("Choose one: --verify-only OR --initial OR --incremental")

    db = DBClient()
    browser = SeleniumDriver()
    pipe = Pipeline(db, browser)

    try:
        browser.get(settings.BINA_BASE_URL)

        if args.verify_only:
            ok = pipe.verify()
            print(f"[verify] access ok: {ok}")
            return

        if args.initial:
            max_new = settings.MAX_LISTINGS_INITIAL
        else:
            max_new = settings.MAX_LISTINGS_INCREMENTAL

        inserted = pipe.run(max_new=max_new)
        mode = "initial" if args.initial else "incremental"
        print(f"[{mode}] inserted new rows: {inserted}")

    finally:
        browser.close()
        db.close()


if __name__ == "__main__":
    main()
