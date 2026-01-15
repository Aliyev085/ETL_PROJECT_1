# /opt/Etl_server_project_1/src/bina/db.py
# GOOGLE-LEVEL DB LAYER FIXED FOR AIRFLOW + SELENIUM
# ---------------------------------------------------
#db.py file
import psycopg2
import psycopg2.extras
from datetime import datetime

from bina.config import settings


# ===========================================================
# DB CONNECTION
# ===========================================================
def get_conn():
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD
    )


def now_utc():
    return datetime.utcnow()


# ===========================================================
# CHECK IF ALREADY SCRAPED
# ===========================================================
def is_listing_scraped(listing_id):
    """
    Check if a listing has already been scraped (is_scraped = True).
    Returns True if already scraped, False otherwise.
    """
    sql = """
    SELECT is_scraped 
    FROM bina_apartments 
    WHERE listing_id = %s;
    """
    
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, (listing_id,))
        result = cur.fetchone()
        
        if result is None:
            # Listing doesn't exist yet
            return False
            
        return result[0] is True
        
    except Exception as e:
        print(f"[DB ERROR] CHECK SCRAPED FAILED: {e}")
        # On error, return False to allow scraping attempt
        return False
    finally:
        if conn:
            conn.close()


# ===========================================================
# FAST SCRAPER UPSERT
# ===========================================================
def upsert_listing_fast(**kw):
    sql = """
    INSERT INTO bina_apartments (
        listing_id, url, title,
        price_azn, area_sqm, price_per_sqm,
        rooms, floor_current, floor_total,
        has_mortgage, has_deed,
        location_area, location_city, owned_type,
        posted_at, scraped_at
    )
    VALUES (
        %(listing_id)s, %(url)s, %(title)s,
        %(price_azn)s, %(area_sqm)s, %(price_per_sqm)s,
        %(rooms)s, %(floor_current)s, %(floor_total)s,
        %(has_mortgage)s, %(has_deed)s,
        %(location_area)s, %(location_city)s, %(owned_type)s,
        %(posted_at)s, %(scraped_at)s
    )
    ON CONFLICT (listing_id)
    DO UPDATE SET
        url = EXCLUDED.url,
        title = EXCLUDED.title,
        price_azn = EXCLUDED.price_azn,
        area_sqm = EXCLUDED.area_sqm,
        price_per_sqm = EXCLUDED.price_per_sqm,
        rooms = EXCLUDED.rooms,
        floor_current = EXCLUDED.floor_current,
        floor_total = EXCLUDED.floor_total,
        has_mortgage = EXCLUDED.has_mortgage,
        has_deed = EXCLUDED.has_deed,
        location_area = EXCLUDED.location_area,
        location_city = EXCLUDED.location_city,
        owned_type = EXCLUDED.owned_type,
        posted_at = EXCLUDED.posted_at,
        scraped_at = EXCLUDED.scraped_at;
    """

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, kw)
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print("[DB ERROR] FAST UPSERT FAILED:", e)
        raise
    finally:
        if conn:
            conn.close()


# ===========================================================
# DETAIL SCRAPER — **UPDATED: UPDATE ONLY, NEVER INSERT**
# ===========================================================
def upsert_listing_detail(**kw):
    """
    Detail scraper writes:
      listing_id, description, posted_by,
      contact_number, view_count,
      is_constructed, is_scraped

    IMPORTANT:
      • ONLY updates existing row
      • NEVER inserts new ones
      • Prevents null required fields
    """

    sql = """
    UPDATE bina_apartments
    SET
        description = %(description)s,
        posted_by = %(posted_by)s,
        contact_number = %(contact_number)s,
        view_count = %(view_count)s,
        is_constructed = %(is_constructed)s,
        is_scraped = %(is_scraped)s
    WHERE listing_id = %(listing_id)s;
    """

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, kw)

        # If no row exists → skip silently
        if cur.rowcount == 0:
            print(f"[DB WARNING] DETAIL SKIPPED — listing_id {kw['listing_id']} does not exist yet")
            conn.commit()
            return

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print("[DB ERROR] DETAIL UPDATE FAILED:", e)
        raise
    finally:
        if conn:
            conn.close()
