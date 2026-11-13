from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, JSON, UniqueConstraint, Index, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from app.core.config import settings

Base = declarative_base()


class Job(Base):
    """Offre d'emploi agrégée depuis plusieurs sources."""
    __tablename__ = "jobs"

    id               = Column(Integer, primary_key=True, index=True)
    # Identification
    external_id      = Column(String(512), nullable=True)    # ID sur la source
    url              = Column(Text, unique=True, nullable=False)
    url_hash         = Column(String(64), unique=True, index=True)  # MD5 de l'URL pour dédup rapide

    # Contenu principal
    title            = Column(String(512), nullable=False)
    company          = Column(String(255), nullable=True)
    location         = Column(String(255), nullable=True)
    description      = Column(Text, nullable=True)
    description_short= Column(String(1000), nullable=True)  # Premier 1000 chars pour preview

    # Classification
    source           = Column(String(100), nullable=False, index=True)   # emploi_dakar, senjob, etc.
    job_type         = Column(String(50), nullable=True, index=True)     # stage, CDI, CDD, alternance
    is_remote        = Column(Boolean, default=False)

    # Compétences extraites
    skills_extracted = Column(JSON, default=list)   # ["python", "docker", ...]
    skills_matched   = Column(JSON, default=list)   # Intersection avec profil user
    skills_missing   = Column(JSON, default=list)   # Dans l'offre mais pas dans le profil

    # Scoring NLP
    matching_score   = Column(Float, default=0.0, index=True)  # 0.0 → 1.0
    score_breakdown  = Column(JSON, default=dict)   # {skills: 0.7, title: 0.5, ...}
    match_explanation= Column(Text, nullable=True)

    # Salaire
    salary_raw       = Column(String(255), nullable=True)
    salary_min       = Column(Integer, nullable=True)
    salary_max       = Column(Integer, nullable=True)

    # Dates
    posted_date      = Column(DateTime(timezone=True), nullable=True)
    scraped_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    # Statut
    status           = Column(String(20), default="active")  # active, expired, applied
    is_favorite      = Column(Boolean, default=False)
    raw_data         = Column(JSON, nullable=True)  # Données brutes pour debug

    __table_args__ = (
        Index("idx_jobs_score_source", "matching_score", "source"),
        Index("idx_jobs_scraped_at", "scraped_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "source": self.source,
            "job_type": self.job_type,
            "is_remote": self.is_remote,
            "description_short": self.description_short,
            "skills_extracted": self.skills_extracted or [],
            "skills_matched": self.skills_matched or [],
            "skills_missing": self.skills_missing or [],
            "matching_score": self.matching_score,
            "score_breakdown": self.score_breakdown or {},
            "match_explanation": self.match_explanation,
            "salary_raw": self.salary_raw,
            "posted_date": str(self.posted_date) if self.posted_date else None,
            "scraped_at": str(self.scraped_at) if self.scraped_at else None,
            "url": self.url,
            "status": self.status,
            "is_favorite": self.is_favorite,
        }


class ScrapeRun(Base):
    """Historique des runs de scraping."""
    __tablename__ = "scrape_runs"

    id           = Column(Integer, primary_key=True)
    source       = Column(String(100), nullable=False)
    started_at   = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status       = Column(String(20), default="running")  # running, success, failed
    jobs_found   = Column(Integer, default=0)
    jobs_new     = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    error_msg    = Column(Text, nullable=True)
    duration_sec = Column(Float, nullable=True)


def get_engine():
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True)


def init_db():
    """Crée toutes les tables si elles n'existent pas."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées / vérifiées.")
