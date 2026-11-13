"""
Scraper pour senjob.com — principal job board sénégalais.
Approche : paginer la liste des offres IT, puis scraper chaque détail.
"""

import re
from urllib.parse import urljoin, urlencode
from loguru import logger
from app.scraping.base_scraper import BaseScraper, RawJob


class SenJobScraper(BaseScraper):

    SOURCE_NAME = "senjob"
    BASE_URL = "https://www.senjob.com"

    SEARCH_PARAMS = [
        {"secteur": "informatique-telecom"},
        {"secteur": "ingenierie-technique"},
        {"keyword": "réseau systèmes"},
        {"keyword": "cybersécurité"},
        {"keyword": "cloud devops"},
        {"keyword": "data engineer"},
        {"keyword": "stage informatique"},
    ]

    async def scrape(self) -> list[RawJob]:
        jobs = []
        seen_urls: set[str] = set()

        for params in self.SEARCH_PARAMS:
            param_jobs = await self._scrape_search(params, seen_urls)
            jobs.extend(param_jobs)

        return jobs

    async def _scrape_search(self, params: dict, seen_urls: set) -> list[RawJob]:
        jobs = []

        for page in range(1, 6):  # Max 5 pages
            query = urlencode({**params, "page": page})
            url = f"{self.BASE_URL}/emploi?{query}"
            soup = await self._fetch(url)

            if soup is None:
                break

            links = self._extract_job_links(soup)
            if not links:
                break

            for job_url, title_hint in links:
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)
                raw_job = await self._scrape_job_page(job_url, title_hint)
                if raw_job:
                    jobs.append(raw_job)

        return jobs

    def _extract_job_links(self, soup) -> list[tuple[str, str]]:
        """Extrait les liens vers les pages d'offres depuis une page de résultats."""
        results = []

        # Sélecteurs typiques de senjob.com
        candidates = soup.find_all("a", href=True)

        for a in candidates:
            href = a["href"]
            # Les offres senjob ont souvent /offre/ ou /emploi/ dans l'URL
            if any(pattern in href for pattern in ["/offre/", "/emploi/", "/job/"]):
                full_url = href if href.startswith("http") else urljoin(self.BASE_URL, href)
                # Ignorer les pages de navigation
                if any(skip in full_url for skip in ["page=", "secteur=", "?p="]):
                    continue
                title = self.clean_text(a.get_text())
                if title and len(title) > 4:
                    results.append((full_url, title))

        # Déduplication par URL
        seen = set()
        unique = []
        for url, title in results:
            if url not in seen:
                seen.add(url)
                unique.append((url, title))

        return unique[:25]

    async def _scrape_job_page(self, url: str, title_hint: str) -> RawJob | None:
        soup = await self._fetch(url)
        if soup is None:
            return None

        # ── Titre ────────────────────────────────────────────────────────────
        title = None
        for sel in ["h1.job-title", "h1.titre", "h1", ".intitule-poste"]:
            el = soup.select_one(sel)
            if el:
                t = self.clean_text(el.get_text())
                if t and len(t) > 5:
                    title = t
                    break
        title = title or title_hint

        # ── Entreprise ───────────────────────────────────────────────────────
        company = None
        for sel in [".company", ".recruteur", ".nom-entreprise", "span.employeur",
                    "div.company-info h2", "a.entreprise"]:
            el = soup.select_one(sel)
            if el:
                c = self.clean_text(el.get_text())
                if c and 2 < len(c) < 200:
                    company = c
                    break

        # ── Localisation ─────────────────────────────────────────────────────
        location = "Sénégal"
        for sel in [".lieu", ".location", ".ville", "span.localisation",
                    "div.localisation", ".adresse"]:
            el = soup.select_one(sel)
            if el:
                loc = self.clean_text(el.get_text())
                if loc and 2 < len(loc) < 150:
                    location = loc
                    break

        # ── Type de contrat ───────────────────────────────────────────────────
        job_type_hint = None
        for sel in [".type-contrat", ".contrat", ".contract-type",
                    "span.cdi", "span.stage", ".type"]:
            el = soup.select_one(sel)
            if el:
                job_type_hint = self.clean_text(el.get_text())
                break

        # ── Description ──────────────────────────────────────────────────────
        description = None
        for sel in [".description-poste", ".job-description", ".contenu-offre",
                    "#annonce", ".annonce-detail", "div.detail"]:
            el = soup.select_one(sel)
            if el:
                desc = self.clean_text(el.get_text())
                if desc and len(desc) > 80:
                    description = desc
                    break

        if not description:
            all_text = []
            for tag in soup.find_all(["p", "li", "div"]):
                text = self.clean_text(tag.get_text(separator=" "))
                if text and len(text) > 30:
                    all_text.append(text)
            description = " ".join(all_text[:20])

        # ── Salaire ───────────────────────────────────────────────────────────
        salary_raw = None
        text_lower = (description or "").lower()
        match = re.search(r'\d[\d\s.]*(?:fcfa|xof|f\.?cfa|franc)', text_lower)
        if match:
            salary_raw = match.group(0)[:80]

        return RawJob(
            url=url,
            title=title,
            company=company,
            location=location,
            description=self.truncate(description, 3000),
            salary_raw=salary_raw,
            job_type_hint=job_type_hint,
            source=self.SOURCE_NAME,
            raw_data={"scraped_from": url},
        )
