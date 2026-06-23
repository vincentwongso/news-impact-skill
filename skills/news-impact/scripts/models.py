from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator

Direction = Literal["bullish", "bearish", "neutral"]
Severity = Literal["low", "medium", "high"]
Horizon = Literal["intraday", "swing", "longterm"]


def make_id(title: str, url: str, published: datetime) -> str:
    raw = f"{title}{url}{published.isoformat()}".encode()
    return hashlib.sha256(raw).hexdigest()


class NewsItem(BaseModel):
    title: str
    summary: str
    url: str
    source: str
    published: datetime
    sentiment: float | None = None
    matched_symbols: list[str] = Field(default_factory=list)

    @field_validator("published")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        return make_id(self.title, self.url, self.published)


class Impact(BaseModel):
    symbol: str
    direction: Direction
    severity: Severity
    horizon: Horizon
    confidence: float = Field(ge=0.0, le=1.0)
    why: str


class Briefing(BaseModel):
    headline: str
    source: str
    published: datetime
    impacts: list[Impact]
    grounding: str


class ItemImpacts(BaseModel):
    id: str
    impacts: list[Impact]
    grounding: str


class RankerOutput(BaseModel):
    results: list[ItemImpacts]
