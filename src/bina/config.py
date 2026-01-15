# /opt/Etl_server_project_1/src/bina/config.py
# GOOGLE-LEVEL CONFIG SYSTEM FOR SELENIUM + AIRFLOW ETL
# -----------------------------------------------------
# Loads .env safely, validates defaults, provides
# stable scraper settings for all modules.
# -----------------------------------------------------
#config.py file

from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv


# ===========================================================
# LOAD ENVIRONMENT
# ===========================================================
ENV_PATH = "/opt/Etl_server_project_1/.env"

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()  # fallback for debugging outside Airflow


# ===========================================================
# SETTINGS MODEL
# ===========================================================
@dataclass(frozen=True)
class Settings:

    # -----------------------------------------
    # BASE URLS
    # -----------------------------------------
    BINA_BASE_URL: str = os.getenv(
        "BINA_BASE_URL",
        "https://bina.az/baki/alqi-satqi"
    )

    # -----------------------------------------
    # SELENIUM CONFIG
    # -----------------------------------------
    SELENIUM_PAGE_LOAD_TIMEOUT: int = int(
        os.getenv("SELENIUM_PAGE_LOAD_TIMEOUT", 15)
    )

    SELENIUM_RETRY_COUNT: int = int(
        os.getenv("SELENIUM_RETRY_COUNT", 2)
    )

    SELENIUM_WAIT_AFTER_LOAD: float = float(
        os.getenv("SELENIUM_WAIT_AFTER_LOAD", 2.0)
    )

    # -----------------------------------------
    # SCROLLING (FAST SCRAPER)
    # -----------------------------------------
    SCROLL_ROUNDS_LIMIT: int = int(
        os.getenv("BINA_SCROLL_ROUNDS_LIMIT", 20)
    )
    SCROLL_SLEEP: float = float(
        os.getenv("BINA_SCROLL_SLEEP", 1.0)
    )

    # -----------------------------------------
    # SCRAPER LIMITS
    # -----------------------------------------
    FAST_SCRAPER_LIMIT: int = int(
        os.getenv("FAST_SCRAPER_LIMIT", 500)
    )
    DETAIL_SCRAPER_LIMIT: int = int(
        os.getenv("DETAIL_SCRAPER_LIMIT", 200)
    )

    # -----------------------------------------
    # DATABASE CONFIG
    # -----------------------------------------
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "etlserver_db")
    DB_USER: str = os.getenv("DB_USER", "Aliyev_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # -----------------------------------------
    # RABBITMQ CONFIG
    # -----------------------------------------
    RABBIT_HOST: str = os.getenv("RABBIT_HOST", "rabbitmq")
    RABBIT_PORT: int = int(os.getenv("RABBIT_PORT", 5672))
    RABBIT_USER: str = os.getenv("RABBIT_USER", "")
    RABBIT_PASSWORD: str = os.getenv("RABBIT_PASSWORD", "")
    RABBIT_QUEUE: str = os.getenv("RABBIT_QUEUE", "listing_queue")

    # Toggle for headless Selenium
    HEADLESS: bool = True


# ===========================================================
# EXPORT SETTINGS
# ===========================================================
settings = Settings()
