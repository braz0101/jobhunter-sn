"""Celery application et beat schedule."""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "jobhunter",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.scraping_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Dakar",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    # ── Planification automatique ───────────────────────────────────────────
    beat_schedule={
        # Scraping complet 3x/jour : 7h, 13h, 19h (heure de Dakar)
        "scrape-all-morning": {
            "task": "app.tasks.scraping_tasks.run_all_scrapers",
            "schedule": crontab(hour=7, minute=0),
            "options": {"queue": "scraping"},
        },
        "scrape-all-afternoon": {
            "task": "app.tasks.scraping_tasks.run_all_scrapers",
            "schedule": crontab(hour=13, minute=0),
            "options": {"queue": "scraping"},
        },
        "scrape-all-evening": {
            "task": "app.tasks.scraping_tasks.run_all_scrapers",
            "schedule": crontab(hour=19, minute=0),
            "options": {"queue": "scraping"},
        },
        # Nettoyage hebdomadaire des offres expirées
        "cleanup-expired-jobs": {
            "task": "app.tasks.scraping_tasks.cleanup_old_jobs",
            "schedule": crontab(day_of_week="sunday", hour=2),
        },
    },

    task_routes={
        "app.tasks.scraping_tasks.run_all_scrapers": {"queue": "scraping"},
        "app.tasks.scraping_tasks.run_single_scraper": {"queue": "scraping"},
        "app.tasks.scraping_tasks.cleanup_old_jobs": {"queue": "default"},
    },
)
