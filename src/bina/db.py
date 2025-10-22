from __future__ import annotations
from typing import Iterable, Set, Sequence
from contextlib import contextmanager
import psycopg
from psycopg import sql

from .config import settings
from .models import Flat


class DBClient:
    """Database client for interacting with bina_apartments table."""

    def __init__(self) -> None:
        self._conn = psycopg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )
        self._conn.autocommit = False  # manual commit mode

    @contextmanager
    def cursor(self):
        """Provide a database cursor context with automatic cleanup."""
        with self._conn.cursor() as cur:
            yield cur

    def close(self) -> None:
        """Close the connection cleanly."""
        try:
            self._conn.close()
        except Exception:
            pass

    # ---------- queries ----------
    def listing_ids_exist(self, listing_ids: Iterable[int]) -> Set[int]:
        """Return set of listing IDs that already exist in the database."""
        ids = list({i for i in listing_ids if i is not None})
        if not ids:
            return set()

        placeholders = sql.SQL(",").join(sql.Placeholder() * len(ids))
        query = sql.SQL(
            "SELECT listing_id FROM public.bina_apartments WHERE listing_id IN ({ids})"
        ).format(ids=placeholders)

        with self.cursor() as cur:
            cur.execute(query, ids)
            rows = cur.fetchall()

        return {r[0] for r in rows}

    def insert_new(self, flats: Sequence[Flat]) -> int:
        """Insert new listings, skip duplicates via ON CONFLICT DO NOTHING."""
        if not flats:
            return 0

        # Updated columns (removed is_renovated)
        cols = [
            "listing_id", "url", "title", "price_azn", "price_per_sqm",
            "rooms", "area_sqm", "floor_current", "floor_total",
            "location_area", "location_city", "owner_type",
            "has_mortgage", "has_deed", "posted_at"
        ]

        # Prepare parameter values
        values = [[getattr(f, c) for c in cols] for f in flats]
        placeholders = "(" + ",".join(["%s"] * len(cols)) + ")"
        insert_sql = f"""
            INSERT INTO public.bina_apartments (
                {', '.join(cols)}
            )
            VALUES {', '.join([placeholders] * len(values))}
            ON CONFLICT (listing_id) DO NOTHING
        """

        flat_params = [v for row in values for v in row]

        try:
            with self.cursor() as cur:
                cur.execute(insert_sql, flat_params)
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            print(f"[DB ERROR] Insert failed: {e}")
            raise

        return len(flats)
