from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class JobBase(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    source: str
    job_type: Optional[str] = None
    is_remote: bool = False


class JobResponse(JobBase):
    id: int
    url: str
    description_short: Optional[str] = None
    skills_extracted: List[str] = []
    skills_matched: List[str] = []
    skills_missing: List[str] = []
    matching_score: float = 0.0
    score_breakdown: dict = {}
    match_explanation: Optional[str] = None
    salary_raw: Optional[str] = None
    posted_date: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    status: str = "active"
    is_favorite: bool = False

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    total: int
    jobs: List[JobResponse]
    page: int
    per_page: int
    has_more: bool


class JobFilters(BaseModel):
    source: Optional[str] = None
    job_type: Optional[str] = None
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_remote: Optional[bool] = None
    location_contains: Optional[str] = None
    skill_contains: Optional[str] = None
    search: Optional[str] = None
    status: str = "active"
    sort_by: str = "matching_score"  # matching_score | scraped_at
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class ScrapeRequest(BaseModel):
    source: Optional[str] = None  # None = all sources


class ScrapeStat(BaseModel):
    source: str
    total: int
    avg_score: float
    high_match: int   # score >= 0.75
    medium_match: int # 0.50 <= score < 0.75
