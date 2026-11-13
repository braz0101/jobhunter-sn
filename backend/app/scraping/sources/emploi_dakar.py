"""
Scraper pour emploi-dakar.com (ou senuplus.com).
Structure : liste paginée → page détail de chaque offre.

NOTE : La structure HTML exacte peut changer. En cas de 0 résultat,
inspecter le sélecteur CSS dans _parse_listing() et _parse_detail().
"""

import re
from loguru import logger
from app.scraping.base_scraper import BaseScraper, RawJob


class EmploiDakarScraper(BaseScraper):

    SOURCE_NAME = "emploi_dakar"
    BASE_URL = "https://www.emploi-dakar.com"

    # Mots-clés IT pertinents pour filtrer sur la source
    SEARCH_KEYWORDS = [
        "informatique", "réseau", "systèmes", "cybersécurité",
        "cloud", "devops", "data", "développeur", "ingénieur",
        "télécoms", "linux", "stage informatique",
    ]

    async def scrape(self) -> list[RawJob]:
        jobs = []
        seen_urls: set[str] = set()

        for keyword in self.SEARCH_KEYWORDS[:6]:  # Limite par polite scraping
            kw_jobs = await self._scrape_keyword(keyword, seen_urls)
            jobs.extend(kw_jobs)
            logger.info(f"[emploi_dakar] '{keyword}' → {len(kw_jobs)} offres")

        return jobs

    async def _scrape_keyword(self, keyword: str, seen_urls: set) -> list[RawJob]:
        """Scrape les résultats de recherche pour un mot-clé donné."""
        jobs = []
        page = 1

        while page <= 5:  # Max 5 pages par keyword
            url = f"{self.BASE_URL}/emploi/{self._slug(keyword)}/page/{page}"
            soup = await self._fetch(url)

            if soup is None:
                break

            job_links = self._parse_listing(soup)
            if not job_links:
                break

            for job_url, title_preview in job_links:
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                raw_job = await self._parse_detail(job_url, title_preview)
                if raw_job:
                    jobs.append(raw_job)

            page += 1

        return jobs

    def _parse_listing(self, soup) -> list[tuple[str, str]]:
        """
        Extrait les URLs et titres depuis la page de listing.
        Sélecteurs à ajuster selon la structure actuelle du site.
        """
        results = []

        # ── Tentative 1 : Structure standard type job-board ──────────────────
        # Essayer plusieurs sélecteurs communs
        selectors = [
            "article.job-item h2 a",
            "div.job-listing h3 a",
            "div.job-item a.job-title",
            "li.job a.title",
            "h2.job-title a",
            "a.poste",  # Senuplus-style
            "div.offre-emploi h2 a",
        ]

        for sel in selectors:
            links = soup.select(sel)
            if links:
                for a in links[:20]:  # Max 20 par page
                    href = a.get("href", "")
                    if href and "/emploi/" in href:
                        full_url = href if href.startswith("http") else self.BASE_URL + href
                        results.append((full_url, self.clean_text(a.get_text()) or ""))
                break

        # ── Fallback : tous les liens vers des offres ─────────────────────────
        if not results:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/emploi/" in href and "/page/" not in href:
                    full_url = href if href.startswith("http") else self.BASE_URL + href
                    text = self.clean_text(a.get_text())
                    if text and len(text) > 5:
                        results.append((full_url, text))

        return results[:20]

    async def _parse_detail(self, url: str, title_hint: str) -> RawJob | None:
        """Scrape la page de détail d'une offre."""
        soup = await self._fetch(url)
        if soup is None:
            return None

        # ── Titre ─────────────────────────────────────────────────────────────
        title = None
        for sel in ["h1.job-title", "h1.titre-offre", "h1", "title"]:
            el = soup.select_one(sel)
            if el:
                title = self.clean_text(el.get_text())
                if title and len(title) > 5:
                    break
        title = title or title_hint

        # ── Entreprise ────────────────────────────────────────────────────────
        company = None
        for sel in [".company-name", ".entreprise", ".recruteur", "span.company",
                    "div.employeur", "a.nom-entreprise"]:
            el = soup.select_one(sel)
            if el:
                company = self.clean_text(el.get_text())
                break

        # ── Localisation ──────────────────────────────────────────────────────
        location = "Dakar, Sénégal"  # Default pour cette source
        for sel in [".location", ".localisation", ".lieu", "span.ville",
                    "div.localisation", ".lieu-travail"]:
            el = soup.select_one(sel)
            if el:
                loc_text = self.clean_text(el.get_text())
                if loc_text and len(loc_text) > 2:
                    location = loc_text
                    break

        # ── Description ───────────────────────────────────────────────────────
        description = None
        for sel in [".job-description", ".description-offre", ".content-offre",
                    "#description", "div.offre-detail", ".annonce-corps",
                    "div.detail-offre", "section.description"]:
            el = soup.select_one(sel)
            if el:
                description = self.clean_text(el.get_text())
                if description and len(description) > 50:
                    break

        if not description:
            # Fallback : paragraphes principaux
            paragraphs = soup.find_all("p")
            description = " ".join(
                self.clean_text(p.get_text()) or ""
                for p in paragraphs if p.get_text(strip=True)
            )[:3000]

        # ── Salaire ───────────────────────────────────────────────────────────
        salary_raw = None
        for pattern in [r'\d[\d\s]*(?:fcfa|xof|f cfa)', r'salaire\s*:?\s*[^\n]+']:
            match = re.search(pattern, (description or "").lower())
            if match:
                salary_raw = match.group(0)[:100]
                break

        return RawJob(
            url=url,
            title=title or title_hint,
            company=company,
            location=location,
            description=self.truncate(description, 3000),
            salary_raw=salary_raw,
            source=self.SOURCE_NAME,
            raw_data={"source_url": url},
        )

    @staticmethod
    def _slug(text: str) -> str:
        """Convertit un texte en slug URL."""
        from unidecode import unidecode
        return re.sub(r'[^a-z0-9]+', '-', unidecode(text).lower()).strip('-')
