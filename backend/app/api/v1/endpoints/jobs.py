from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.db.models import Job
from app.db.session import get_db
from app.schemas.job import JobResponse, JobListResponse, JobFilters, ScrapeStat

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=JobListResponse)
def list_jobs(
    db: Session = Depends(get_db),
    source: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    is_remote: Optional[bool] = Query(None),
    location_contains: Optional[str] = Query(None),
    skill: Optional[str] = Query(None, description="Filtre par compétence"),
    search: Optional[str] = Query(None, description="Recherche dans titre/entreprise"),
    status: str = Query("active"),
    sort_by: str = Query("matching_score", regex="^(matching_score|scraped_at)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Liste les offres avec filtres et pagination."""
    query = db.query(Job).filter(Job.status == status)

    if source:
        query = query.filter(Job.source == source)
    if job_type:
        query = query.filter(Job.job_type == job_type)
    if min_score > 0:
        query = query.filter(Job.matching_score >= min_score)
    if is_remote is not None:
        query = query.filter(Job.is_remote == is_remote)
    if location_contains:
        query = query.filter(Job.location.ilike(f"%{location_contains}%"))
    if search:
        query = query.filter(
            or_(
                Job.title.ilike(f"%{search}%"),
                Job.company.ilike(f"%{search}%"),
            )
        )
    if skill:
        # Filtre JSON : compétence présente dans skills_extracted
        query = query.filter(Job.skills_extracted.contains([skill.lower()]))

    total = query.count()

    if sort_by == "matching_score":
        query = query.order_by(desc(Job.matching_score))
    else:
        query = query.order_by(desc(Job.scraped_at))

    offset = (page - 1) * per_page
    jobs = query.offset(offset).limit(per_page).all()

    return JobListResponse(
        total=total,
        jobs=[JobResponse.model_validate(j) for j in jobs],
        page=page,
        per_page=per_page,
        has_more=(offset + per_page) < total,
    )


@router.get("/stats", response_model=list[ScrapeStat])
def get_stats(db: Session = Depends(get_db)):
    """Stats par source : total, score moyen, nb high/medium match."""
    from sqlalchemy import func
    from app.core.config import settings

    rows = (
        db.query(
            Job.source,
            func.count(Job.id).label("total"),
            func.avg(Job.matching_score).label("avg_score"),
        )
        .filter(Job.status == "active")
        .group_by(Job.source)
        .order_by(desc("total"))
        .all()
    )

    stats = []
    for row in rows:
        high = db.query(func.count(Job.id)).filter(
            Job.source == row.source,
            Job.matching_score >= settings.SCORE_THRESHOLD_HIGH,
            Job.status == "active",
        ).scalar()
        medium = db.query(func.count(Job.id)).filter(
            Job.source == row.source,
            Job.matching_score >= settings.SCORE_THRESHOLD_MEDIUM,
            Job.matching_score < settings.SCORE_THRESHOLD_HIGH,
            Job.status == "active",
        ).scalar()
        stats.append(ScrapeStat(
            source=row.source,
            total=row.total,
            avg_score=round(float(row.avg_score or 0), 3),
            high_match=high or 0,
            medium_match=medium or 0,
        ))
    return stats


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Offre non trouvée")
    return JobResponse.model_validate(job)


@router.patch("/{job_id}/favorite")
def toggle_favorite(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Offre non trouvée")
    job.is_favorite = not job.is_favorite
    db.commit()
    return {"id": job_id, "is_favorite": job.is_favorite}


@router.patch("/{job_id}/status")
def update_status(job_id: int, status: str, db: Session = Depends(get_db)):
    valid_statuses = ["active", "applied", "expired", "rejected"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs: {valid_statuses}")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Offre non trouvée")
    job.status = status
    db.commit()
    return {"id": job_id, "status": status}
