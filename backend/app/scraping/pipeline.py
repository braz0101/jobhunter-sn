"""
Pipeline de scraping.
Coordonne tous les scrapers, applique le NLP matching, persiste en PostgreSQL.
"""

import asyncio
import hashlib
from datetime import datetime
from loguru import logger

from app.db.models import Job, ScrapeRun, init_db
from app.db.session import get_db_session
from app.nlp.matcher import match_job
from app.scraping.base_scraper import RawJob
from app.scraping.sources.emploi_dakar import EmploiDakarScraper
from app.scraping.sources.senjob import SenJobScraper
from app.scraping.sources.novojob import NovojobScraper, GoogleJobsScraper


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

class ScrapingPipeline:

    # Scrapers actifs (ajoutez en ici pour étendre)
    SCRAPERS = [
        EmploiDakarScraper,
        SenJobScraper,
        NovojobScraper,
        GoogleJobsScraper,
    ]

    async def run_all(self) -> dict:
        """Lance tous les scrapers en parallèle et persiste les résultats."""
        init_db()  # Création des tables si besoin
        logger.info("🚀 Pipeline démarré")

        # Lancer tous les scrapers en parallèle
        tasks = [self._run_scraper(ScraperClass) for ScraperClass in self.SCRAPERS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Agréger les stats
        total_new = 0
        total_updated = 0
        source_stats = {}

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Pipeline error: {result}")
                continue
            if isinstance(result, dict):
                src = result.get("source", "unknown")
                source_stats[src] = result
                total_new += result.get("new", 0)
                total_updated += result.get("updated", 0)

        summary = {
            "total_new": total_new,
            "total_updated": total_updated,
            "sources": source_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info(f"✅ Pipeline terminé : {total_new} nouvelles, {total_updated} mises à jour")
        return summary

    async def run_source(self, source_name: str) -> dict:
        """Lance un seul scraper par son nom."""
        for ScraperClass in self.SCRAPERS:
            if ScraperClass.SOURCE_NAME == source_name:
                return await self._run_scraper(ScraperClass)
        raise ValueError(f"Source inconnue : {source_name}")

    async def _run_scraper(self, ScraperClass) -> dict:
        """Exécute un scraper et persiste les RawJobs."""
        scraper = ScraperClass()
        source = ScraperClass.SOURCE_NAME
        started_at = datetime.utcnow()
        new_count = 0
        updated_count = 0

        with get_db_session() as db:
            run = ScrapeRun(source=source, status="running")
            db.add(run)
            db.flush()
            run_id = run.id

        try:
            raw_jobs = await scraper.scrape_safe()
            logger.info(f"[{source}] {len(raw_jobs)} offres brutes récupérées")

            for raw_job in raw_jobs:
                is_new = await self._persist_job(raw_job)
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1

        except Exception as e:
            logger.error(f"[{source}] Pipeline error: {e}")
            with get_db_session() as db:
                run = db.query(ScrapeRun).get(run_id)
                if run:
                    run.status = "failed"
                    run.error_msg = str(e)
                    run.completed_at = datetime.utcnow()
            return {"source": source, "new": 0, "updated": 0, "error": str(e)}

        # Mise à jour du run
        duration = (datetime.utcnow() - started_at).total_seconds()
        with get_db_session() as db:
            run = db.query(ScrapeRun).get(run_id)
            if run:
                run.status = "success"
                run.jobs_found = len(raw_jobs)
                run.jobs_new = new_count
                run.jobs_updated = updated_count
                run.completed_at = datetime.utcnow()
                run.duration_sec = duration

        logger.info(f"[{source}] ✅ {new_count} nouvelles | {updated_count} mises à jour | {duration:.1f}s")
        return {"source": source, "new": new_count, "updated": updated_count}

    async def _persist_job(self, raw_job: RawJob) -> bool:
        """
        Persiste une offre en base.
        Returns True si nouvelle offre, False si mise à jour.
        """
        url_hash = hashlib.md5(raw_job.url.encode()).hexdigest()

        # Appliquer le NLP matching
        match_result = match_job(
            title=raw_job.title,
            description=raw_job.description or "",
            location=raw_job.location or "",
            job_type_hint=raw_job.job_type_hint,
        )

        description_short = None
        if raw_job.description:
            description_short = raw_job.description[:1000]

        with get_db_session() as db:
            # Vérifier si l'offre existe déjà (par hash URL)
            existing = db.query(Job).filter(Job.url_hash == url_hash).first()

            if existing:
                # Mise à jour du score si la description a changé
                existing.matching_score = match_result["matching_score"]
                existing.skills_matched  = match_result["skills_matched"]
                existing.skills_missing  = match_result["skills_missing"]
                existing.skills_extracted= match_result["skills_extracted"]
                existing.score_breakdown = match_result["score_breakdown"]
                existing.match_explanation = match_result["match_explanation"]
                return False

            # Nouvelle offre
            job = Job(
                url=raw_job.url,
                url_hash=url_hash,
                external_id=raw_job.external_id,
                title=raw_job.title,
                company=raw_job.company,
                location=raw_job.location,
                description=raw_job.description,
                description_short=description_short,
                source=raw_job.source,
                job_type=match_result["job_type"],
                is_remote=match_result["is_remote"],
                skills_extracted=match_result["skills_extracted"],
                skills_matched=match_result["skills_matched"],
                skills_missing=match_result["skills_missing"],
                matching_score=match_result["matching_score"],
                score_breakdown=match_result["score_breakdown"],
                match_explanation=match_result["match_explanation"],
                salary_raw=raw_job.salary_raw,
                raw_data=raw_job.raw_data,
                status="active",
            )
            db.add(job)
            return True
