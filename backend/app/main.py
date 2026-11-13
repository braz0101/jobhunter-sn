"""
JobHunter SN — Backend FastAPI
Démarrage : uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.db.models import init_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage + nettoyage à l'arrêt."""
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} démarré")
    init_db()
    yield
    logger.info("👋 Arrêt du serveur")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API de recherche d'emploi IT automatisée pour le Sénégal",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS pour le frontend Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://frontend:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/")
def root():
    return {
        "message": f"Bienvenue sur {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
    }
