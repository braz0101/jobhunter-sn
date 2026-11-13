# 🎯 JobHunter SN

Outil de recherche d'emploi automatisé pour les métiers IT au Sénégal.
Scraping multi-sources + NLP matching + Dashboard Streamlit.

## Démarrage rapide

```bash
git clone <repo>
cd jobhunter_sn

# 1. Copier et configurer l'environnement
cp .env.example .env
# (optionnel) Ajouter SERPAPI_KEY pour Google Jobs

# 2. Lancer toute la stack
make up

# 3. Accéder au dashboard
open http://localhost:8501

# 4. Déclencher un premier scraping
make scrape
```

## Services

| Service    | URL                     | Description            |
|------------|-------------------------|------------------------|
| Dashboard  | http://localhost:8501   | Interface Streamlit    |
| API REST   | http://localhost:8000   | FastAPI backend        |
| API Docs   | http://localhost:8000/docs | Swagger UI          |
| PostgreSQL | localhost:5432          | Base de données        |
| Redis      | localhost:6379          | Cache + broker Celery  |

## Architecture

```
Sources (EmploiDakar, SenJob, Novojob, LinkedIn, Google)
    ↓
Celery Workers (Playwright + httpx + BeautifulSoup)
    ↓
NLP Pipeline (Skill extraction + Jaccard matching)
    ↓
PostgreSQL (stockage) + Redis (cache)
    ↓
FastAPI (REST API)
    ↓
Streamlit Dashboard
```

## Ajouter une source de scraping

1. Créer `backend/app/scraping/sources/nouvelle_source.py`
2. Hériter de `BaseScraper`, implémenter `scrape()`
3. Ajouter la classe dans `ScrapingPipeline.SCRAPERS`

## Structure du projet

```
jobhunter_sn/
├── docker-compose.yml
├── .env.example
├── Makefile
├── backend/
│   ├── app/
│   │   ├── core/config.py        ← Settings
│   │   ├── db/models.py          ← SQLAlchemy models
│   │   ├── nlp/
│   │   │   ├── skill_extractor.py ← Dictionnaire IT + extraction
│   │   │   ├── matcher.py         ← Scoring pondéré
│   │   │   └── user_profile.py    ← Profil Ibrahima FALL
│   │   ├── scraping/
│   │   │   ├── base_scraper.py    ← Classe abstraite
│   │   │   ├── pipeline.py        ← Orchestrateur
│   │   │   └── sources/           ← Un fichier par source
│   │   ├── tasks/                 ← Celery tasks + beat schedule
│   │   └── api/v1/               ← FastAPI endpoints
└── frontend/
    └── app/main.py               ← Dashboard Streamlit
```

## Licence
MIT — voir `LICENSE`.
