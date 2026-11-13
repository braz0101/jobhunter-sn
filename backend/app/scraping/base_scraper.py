"""
Classe de base pour tous les scrapers.
Gère : rate limiting, retry, rotation user-agent, déduplication, logging.
"""

import asyncio
import hashlib
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASS – Résultat brut d'un scraper
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RawJob:
    url: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    salary_raw: Optional[str] = None
    posted_date_raw: Optional[str] = None
    job_type_hint: Optional[str] = None
    source: str = ""
    raw_data: dict = field(default_factory=dict)

    @property
    def url_hash(self) -> str:
        return hashlib.md5(self.url.encode()).hexdigest()

    def is_valid(self) -> bool:
        return bool(self.url and self.title and len(self.title) > 3)


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPER DE BASE
# ─────────────────────────────────────────────────────────────────────────────

class BaseScraper(ABC):
    """
    Toute source de scraping hérite de cette classe.
    Implémente `scrape()` qui retourne une liste de RawJob.
    """

    SOURCE_NAME: str = "unknown"
    BASE_URL: str = ""
    KEYWORDS: list[str] = [
        "informatique", "réseau", "systèmes", "cybersécurité", "cloud",
        "devops", "data", "linux", "développeur", "ingénieur", "télécoms",
        "it", "tech", "support informatique", "stage",
    ]

    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._start_time = time.time()

    # ── HTTP ──────────────────────────────────────────────────────────────────

    def _get_headers(self) -> dict:
        return {
            "User-Agent": random.choice(settings.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self.session is None or self.session.is_closed:
            proxies = {}
            if settings.HTTP_PROXY:
                proxies = {"http://": settings.HTTP_PROXY, "https://": settings.HTTPS_PROXY or settings.HTTP_PROXY}
            self.session = httpx.AsyncClient(
                headers=self._get_headers(),
                timeout=settings.SCRAPING_TIMEOUT,
                follow_redirects=True,
                proxies=proxies or None,
            )
        return self.session

    async def _polite_delay(self):
        """Délai aléatoire entre requêtes pour éviter le blocage."""
        delay = random.uniform(settings.SCRAPING_DELAY_MIN, settings.SCRAPING_DELAY_MAX)
        await asyncio.sleep(delay)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=False,
    )
    async def _fetch(self, url: str, **kwargs) -> Optional[BeautifulSoup]:
        """
        Fait une requête GET et retourne un BeautifulSoup.
        Retry automatique sur erreurs HTTP avec back-off exponentiel.
        """
        await self._polite_delay()
        client = await self._get_client()

        try:
            # Rotation user-agent à chaque requête
            client.headers.update({"User-Agent": random.choice(settings.USER_AGENTS)})
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            self._request_count += 1

            logger.debug(f"[{self.SOURCE_NAME}] GET {url} → {response.status_code}")
            return BeautifulSoup(response.text, "lxml")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"[{self.SOURCE_NAME}] Rate limited. Pause 30s...")
                await asyncio.sleep(30)
                raise
            elif e.response.status_code == 403:
                logger.warning(f"[{self.SOURCE_NAME}] 403 Forbidden on {url} — skip")
                return None
            elif e.response.status_code == 404:
                return None
            raise

        except Exception as e:
            logger.error(f"[{self.SOURCE_NAME}] Fetch error {url}: {e}")
            return None

    # ── UTILS ─────────────────────────────────────────────────────────────────

    @staticmethod
    def clean_text(text: Optional[str]) -> Optional[str]:
        """Nettoie les espaces et caractères parasites."""
        if not text:
            return None
        import re
        return re.sub(r'\s+', ' ', text.strip())

    @staticmethod
    def truncate(text: Optional[str], max_len: int = 1000) -> Optional[str]:
        if not text:
            return None
        return text[:max_len] if len(text) > max_len else text

    # ── INTERFACE ABSTRAITE ───────────────────────────────────────────────────

    @abstractmethod
    async def scrape(self) -> list[RawJob]:
        """
        Point d'entrée principal du scraper.
        Doit retourner une liste de RawJob valides.
        """
        ...

    async def scrape_safe(self) -> list[RawJob]:
        """Version safe de scrape() : capture les exceptions, retourne [] si erreur."""
        try:
            jobs = await self.scrape()
            valid_jobs = [j for j in jobs if j.is_valid()]
            logger.info(
                f"[{self.SOURCE_NAME}] {len(valid_jobs)} offres valides "
                f"({self._request_count} requêtes en {time.time()-self._start_time:.1f}s)"
            )
            return valid_jobs
        except Exception as e:
            logger.error(f"[{self.SOURCE_NAME}] Erreur critique scrape: {e}")
            return []
        finally:
            if self.session and not self.session.is_closed:
                await self.session.aclose()
