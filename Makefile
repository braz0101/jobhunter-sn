.PHONY: up down build logs scrape migrate shell-backend shell-db

# ─── INFRASTRUCTURE ───────────────────────────────────────────
up:
	cp -n .env.example .env 2>/dev/null || true
	docker-compose up -d --build
	@echo "✅ JobHunter SN démarré"
	@echo "   Dashboard : http://localhost:8501"
	@echo "   API       : http://localhost:8000"
	@echo "   API Docs  : http://localhost:8000/docs"

down:
	docker-compose down

build:
	docker-compose build --no-cache

logs:
	docker-compose logs -f

logs-worker:
	docker-compose logs -f worker beat

# ─── BASE DE DONNÉES ──────────────────────────────────────────
migrate:
	docker-compose exec backend python -c "from app.db.models import init_db; import asyncio; asyncio.run(init_db())"

reset-db:
	docker-compose exec postgres psql -U jobhunter -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) migrate

# ─── SCRAPING MANUEL ──────────────────────────────────────────
scrape:
	docker-compose exec backend python -c "from app.tasks.scraping_tasks import run_all_scrapers; run_all_scrapers.delay()"
	@echo "🚀 Scraping lancé en arrière-plan (voir logs worker)"

scrape-now:
	docker-compose exec backend python -c "from app.scraping.pipeline import ScrapingPipeline; import asyncio; asyncio.run(ScrapingPipeline().run_all())"

# ─── SHELLS ───────────────────────────────────────────────────
shell-backend:
	docker-compose exec backend bash

shell-db:
	docker-compose exec postgres psql -U jobhunter

# ─── DÉVELOPPEMENT LOCAL (sans Docker) ───────────────────────
install-backend:
	cd backend && pip install -r requirements.txt --break-system-packages

install-frontend:
	cd frontend && pip install -r requirements.txt --break-system-packages

run-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

run-frontend:
	cd frontend && streamlit run app/main.py --server.port 8501

run-worker:
	cd backend && celery -A app.tasks.celery_app worker --loglevel=info

# ─── STATS ────────────────────────────────────────────────────
stats:
	@docker-compose exec postgres psql -U jobhunter -c \
	  "SELECT source, COUNT(*) as total, AVG(matching_score)::numeric(5,2) as avg_score FROM jobs GROUP BY source ORDER BY total DESC;"
