"""Tâches Celery pour le scraping asynchrone."""
import asyncio
from datetime import datetime, timedelta
from loguru import logger

from app.tasks.celery_app import celery_app
from app.db.session import get_db_session
from app.db.models import Job


@celery_app.task(
    name="app.tasks.scraping_tasks.run_all_scrapers",
    bind=True,
    max_retries=2,
    soft_time_limit=1800,  # 30 min max
)
def run_all_scrapers(self):
    """Lance le pipeline complet sur toutes les sources."""
    from app.scraping.pipeline import ScrapingPipeline
    try:
        pipeline = ScrapingPipeline()
        result = asyncio.get_event_loop().run_until_complete(pipeline.run_all())
        logger.info(f"[task:run_all] Done: {result}")
        return result
    except Exception as exc:
        logger.error(f"[task:run_all] Error: {exc}")
        raise self.retry(exc=exc, countdown=300)  # Retry dans 5min


@celery_app.task(
    name="app.tasks.scraping_tasks.run_single_scraper",
    bind=True,
    max_retries=2,
    soft_time_limit=600,
)
def run_single_scraper(self, source_name: str):
    """Lance le scraping pour une source spécifique."""
    from app.scraping.pipeline import ScrapingPipeline
    try:
        pipeline = ScrapingPipeline()
        result = asyncio.get_event_loop().run_until_complete(
            pipeline.run_source(source_name)
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(name="app.tasks.scraping_tasks.cleanup_old_jobs")
def cleanup_old_jobs(days: int = 60):
    """Marque les offres de plus de N jours comme expirées."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    with get_db_session() as db:
        expired = (
            db.query(Job)
            .filter(Job.scraped_at < cutoff, Job.status == "active")
            .all()
        )
        for job in expired:
            job.status = "expired"
        logger.info(f"[cleanup] {len(expired)} offres marquées expirées (>{days}j)")
    return {"expired": len(expired)}
