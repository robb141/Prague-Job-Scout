from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class JobPosting:
    source: str
    source_id: str
    title: str
    company: str
    url: str
    location: str = ""
    district_match: str = ""
    posted_date: str = ""
    company_description: str = ""
    summary: str = ""
    matched_query: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_new: bool = False

    @property
    def stable_id(self) -> str:
        return f"{self.source}:{self.source_id or self.url}"
