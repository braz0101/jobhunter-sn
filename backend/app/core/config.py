from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # ─── APP ────────────────────────────────────────────────
    APP_NAME: str = "JobHunter SN"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ─── DATABASE ───────────────────────────────────────────
    DATABASE_URL: str = "postgresql://jobhunter:change_me@localhost:5432/jobhunter"

    # ─── REDIS ──────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─── CELERY ─────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ─── SCRAPING ───────────────────────────────────────────
    SCRAPING_DELAY_MIN: float = 1.5
    SCRAPING_DELAY_MAX: float = 4.0
    SCRAPING_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    CACHE_TTL_SECONDS: int = 3600  # 1 heure

    HTTP_PROXY: str = ""
    HTTPS_PROXY: str = ""
    SERPAPI_KEY: str = ""  # Pour Google Jobs

    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    ]

    # ─── SCORING ─────────────────────────────────────────────
    # Poids du score final (doivent sommer à 1.0)
    WEIGHT_SKILLS: float = 0.45       # Overlap compétences
    WEIGHT_TITLE: float = 0.25        # Pertinence du titre
    WEIGHT_LOCATION: float = 0.20     # Géographie
    WEIGHT_CONTRACT: float = 0.10     # Type de contrat

    SCORE_THRESHOLD_HIGH: float = 0.75    # Affiché en vert
    SCORE_THRESHOLD_MEDIUM: float = 0.50  # Affiché en orange

    # ─── NOTIFICATIONS ──────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL: str = "ibrahimafall3@esp.sn"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
