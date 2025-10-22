from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file at startup
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # RabbitMQ
    RABBIT_HOST: str = os.getenv("RABBIT_HOST", "localhost")
    RABBIT_PORT: int = int(os.getenv("RABBIT_PORT", 5672))
    RABBIT_USER: str = os.getenv("RABBIT_USER", "guest")
    RABBIT_PASSWORD: str = os.getenv("RABBIT_PASSWORD", "guest")
    RABBIT_QUEUE: str = os.getenv("RABBIT_QUEUE", "listing_queue")

    # Target
    BINA_BASE_URL: str = os.getenv("BINA_BASE_URL", "https://bina.az/baki/menziller")
    HEADLESS: bool = os.getenv("BINA_HEADLESS", "1") == "1"

    # Scroll
    SCROLL_ROUNDS_LIMIT: int = int(os.getenv("BINA_SCROLL_ROUNDS_LIMIT", "25"))
    SCROLL_COOLDOWN_MIN: float = float(os.getenv("BINA_SCROLL_COOLDOWN_MIN", "1.2"))
    SCROLL_COOLDOWN_MAX: float = float(os.getenv("BINA_SCROLL_COOLDOWN_MAX", "2.0"))

    # Batch sizes
    MAX_LISTINGS_INITIAL: int = int(os.getenv("BINA_MAX_LISTINGS_INITIAL", "100"))
    MAX_LISTINGS_INCREMENTAL: int = int(os.getenv("BINA_MAX_LISTINGS_INCREMENTAL", "180"))

    # DB
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "etlserver_db")
    DB_USER: str = os.getenv("DB_USER", "Aliyev_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")


# Create a singleton settings object
settings = Settings()
