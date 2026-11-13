"""
Scraper Novojob.sn + source fallback Google Jobs (via SerpAPI si clé configurée).
"""

import re
from urllib.parse import urljoin, quote_plus
from loguru import logger
from app.scraping.base_scraper import BaseScraper, RawJob
from app.core.config import settings


class NovojobScraper(BaseScraper):

    SOURCE_NAME = "novojob"
    BASE_URL = "https://www.novojob.sn"

    IT_KEYWORDS = [
        "informatique", "réseau", "systèmes", "cybersécurité",
        "cloud computing", "développeur", "data engineer", "devops",
    ]

    async def scrape(self) -> list[RawJob]:
        jobs = []
        seen_urls: set[str] = set()

        for keyword in self.IT_KEYWORDS[:5]:
            kw_jobs = await self._scrape_keyword(keyword, seen_urls)
            jobs.extend(kw_jobs)

        return jobs

    async def _scrape_keyword(self, keyword: str, seen_urls: set) -> list[RawJob]:
        jobs = []
        for page in range(1, 4):
            url = f"{self.BASE_URL}/offres?q={quote_plus(keyword)}&page={page}"
            soup = await self._fetch(url)
            if soup is None:
                break

            links = self._parse_job_links(soup)
            if not links:
                break

            for job_url, title_hint in links:
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)
                raw_job = await self._parse_job(job_url, title_hint)
                if raw_job:
                    jobs.append(raw_job)

        return jobs

    def _parse_job_links(self, soup) -> list[tuple[str, str]]:
        results = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(p in href for p in ["/offre/", "/annonce/", "/job/", "-offre-"]):
                full_url = href if href.startswith("http") else urljoin(self.BASE_URL, href)
                title = self.clean_text(a.get_text())
                if title and 4 < len(title) < 300:
                    results.append((full_url, title))

        seen = set()
        unique = []
        for u, t in results:
            if u not in seen:
                seen.add(u)
                unique.append((u, t))
        return unique[:20]

    async def _parse_job(self, url: str, title_hint: str) -> RawJob | None:
        soup = await self._fetch(url)
        if soup is None:
            return None

        title = None
        for sel in ["h1", ".titre-offre", ".job-title", ".intitule"]:
            el = soup.select_one(sel)
            if el:
                t = self.clean_text(el.get_text())
                if t and len(t) > 5:
                    title = t
                    break

        company = None
        for sel in [".company", ".entreprise", ".recruteur", "div.employeur"]:
            el = soup.select_one(sel)
            if el:
                c = self.clean_text(el.get_text())
                if c and 2 < len(c) < 200:
                    company = c
                    break

        location = "Sénégal"
        for sel in [".localisation", ".location", ".lieu", ".ville"]:
            el = soup.select_one(sel)
            if el:
                loc = self.clean_text(el.get_text())
                if loc and len(loc) > 2:
                    location = loc
                    break

        description = None
        for sel in [".description", ".contenu", ".detail", "#description", ".annonce"]:
            el = soup.select_one(sel)
            if el:
                desc = self.clean_text(el.get_text())
                if desc and len(desc) > 60:
                    description = desc
                    break

        if not description:
            description = self.clean_text(soup.get_text(separator=" "))[:2000]

        return RawJob(
            url=url,
            title=title or title_hint,
            company=company,
            location=location,
            description=self.truncate(description, 3000),
            source=self.SOURCE_NAME,
            raw_data={"url": url},
        )


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE BONUS : Google Jobs via SerpAPI (100 req/mois gratuits)
# ─────────────────────────────────────────────────────────────────────────────

class GoogleJobsScraper(BaseScraper):
    """
    Utilise SerpAPI pour scraper Google Jobs.
    Requiert SERPAPI_KEY dans .env. Si absent, aucune requête n'est faite.
    """

    SOURCE_NAME = "google_jobs"
    SERPAPI_URL = "https://serpapi.com/search"

    SEARCH_QUERIES = [
        "stage informatique Dakar Sénégal",
        "ingénieur réseau systèmes Dakar",
        "cybersécurité emploi Dakar",
        "data engineer cloud Sénégal",
        "développeur emploi Dakar",
        "DevOps Dakar Sénégal",
    ]

    async def scrape(self) -> list[RawJob]:
        if not settings.SERPAPI_KEY:
            logger.info("[google_jobs] SERPAPI_KEY non configurée — source ignorée")
            return []

        jobs = []
        for query in self.SEARCH_QUERIES[:4]:
            results = await self._search_google_jobs(query)
            jobs.extend(results)

        return jobs

    async def _search_google_jobs(self, query: str) -> list[RawJob]:
        """Appelle SerpAPI Google Jobs endpoint."""
        params = {
            "engine": "google_jobs",
            "q": query,
            "location": "Dakar, Senegal",
            "gl": "sn",
            "hl": "fr",
            "api_key": settings.SERPAPI_KEY,
        }
        try:
            client = await self._get_client()
            response = await client.get(self.SERPAPI_URL, params=params)
            response.raise_for_status()
            data = response.json()

            jobs = []
            for item in data.get("jobs_results", [])[:10]:
                job = RawJob(
                    url=item.get("share_link") or item.get("apply_options", [{}])[0].get("link", ""),
                    title=item.get("title", ""),
                    company=item.get("company_name"),
                    location=item.get("location"),
                    description=item.get("description", ""),
                    posted_date_raw=item.get("detected_extensions", {}).get("posted_at"),
                    job_type_hint=", ".join(item.get("detected_extensions", {}).get("schedule_type", [])),
                    source=self.SOURCE_NAME,
                    raw_data=item,
                )
                if job.url:
                    jobs.append(job)
            return jobs

        except Exception as e:
            logger.error(f"[google_jobs] SerpAPI error: {e}")
            return []
