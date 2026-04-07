from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CheckIdParams(BaseModel):
    id: str = Field(..., min_length=16, max_length=128)
    source: str = Field(..., min_length=1, max_length=64)
    published_date: date

    @field_validator("id")
    @classmethod
    def id_hex(cls, v: str) -> str:
        s = v.strip().lower()
        if not all(c in "0123456789abcdef" for c in s):
            raise ValueError("id deve ser hex minúsculo (sha256)")
        if len(s) != 64:
            raise ValueError("id deve ter 64 caracteres (sha256)")
        return s


class ProcessBody(BaseModel):
    date: date
    lookback_days: int = Field(default=1, ge=1, le=120)
    archive: bool = False


class RawArticle(BaseModel):
    id: str
    source: str
    title: str
    url: str
    published_at: str
    summary: str = ""
    ingested_at: str

    model_config = {"extra": "ignore"}


class ProcessedArticle(BaseModel):
    id: str
    source: str
    title: str
    url: str
    published_at: str
    category: str
    score: int
    summary: str
    ingested_at: str
    processing_run_id: str

    def to_delta_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at,
            "category": self.category,
            "score": self.score,
            "summary": self.summary,
            "ingested_at": self.ingested_at,
            "processing_run_id": self.processing_run_id,
        }


class DailyReport(BaseModel):
    date: str
    sections: dict[str, list[dict[str, Any]]]
    sources: list[str]
    llm_insights: dict[str, Any] = Field(default_factory=dict)
