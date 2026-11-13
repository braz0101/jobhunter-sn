from fastapi import APIRouter
from app.api.v1.endpoints.jobs import router as jobs_router
from app.api.v1.endpoints.scraping import router as scraping_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(jobs_router)
api_router.include_router(scraping_router)
