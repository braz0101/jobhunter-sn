"""Endpoint pour déclencher le scraping manuellement."""
from fastapi import APIRouter, BackgroundTasks
from app.schemas.job import ScrapeRequest
from app.tasks.scraping_tasks import run_all_scrapers, run_single_scraper

router = APIRouter(prefix="/scrape", tags=["scraping"])


@router.post("/")
def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Déclenche un scraping via Celery.
    - source=None → toutes les sources
    - source="emploi_dakar" → source unique
    """
    if request.source:
        task = run_single_scraper.delay(request.source)
        return {
            "message": f"Scraping '{request.source}' lancé",
            "task_id": task.id,
        }
    else:
        task = run_all_scrapers.delay()
        return {
            "message": "Scraping complet lancé (toutes sources)",
            "task_id": task.id,
        }


@router.get("/sources")
def list_sources():
    """Liste les sources de scraping disponibles."""
    from app.scraping.sources.emploi_dakar import EmploiDakarScraper
    from app.scraping.sources.senjob import SenJobScraper
    from app.scraping.sources.novojob import NovojobScraper, GoogleJobsScraper
    scrapers = [EmploiDakarScraper, SenJobScraper, NovojobScraper, GoogleJobsScraper]
    return [
        {"source": s.SOURCE_NAME, "base_url": s.BASE_URL}
        for s in scrapers
    ]
