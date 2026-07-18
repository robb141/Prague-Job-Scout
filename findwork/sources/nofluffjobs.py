from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from findwork.config import AppConfig
from findwork.location import district_match, normalize_text
from findwork.models import JobPosting
from findwork.roles import match_role
from findwork.sources.base import JobSource


logger = logging.getLogger(__name__)


# NoFluffJobs browses by category, not free-text query. Map each configured
# role onto the categories whose listings could contain it.
CATEGORY_TERMS = {
    "devops": [
        "devops",
        "sre",
        "site reliability",
        "kubernetes",
        "platform",
        "cloud",
        "aws",
        "azure",
        "gcp",
        "infrastructure",
    ],
    "backend": ["python", "backend", "java", "golang", "node"],
    "data": ["data engineer", "data", "etl", "analytics"],
}


class NoFluffJobsSource(JobSource):
    """Uses the site's search API instead of scraping the listing HTML.

    The HTML listing for city=praha pads its few exact matches with an
    "additional results" block of region-wide remote jobs - mostly Poland -
    and hides the real cities behind a "+1" toggle. The API exposes
    location.places with country codes, so Polish remote postings can be
    filtered out reliably.
    """

    name = "nofluffjobs"
    base_url = "https://nofluffjobs.com"
    api_url = (
        "https://nofluffjobs.com/api/search/posting"
        "?pageTo=1&pageSize=200&salaryCurrency=CZK&salaryPeriod=month&region=cz"
    )

    def fetch(self, config: AppConfig) -> list[JobPosting]:
        jobs: dict[str, JobPosting] = {}

        searches = ["city=praha"] + [
            f"city=remote category={category}"
            for category in self._categories_for_roles(config.roles)
        ]
        for raw_search in searches:
            postings = self._search(raw_search)
            for posting in postings:
                job = self._parse_posting(posting, config)
                if job:
                    jobs.setdefault(job.stable_id, job)
            time.sleep(config.request_delay_seconds)

        return list(jobs.values())

    def _search(self, raw_search: str) -> list[dict]:
        response = self.session.post(self.api_url, json={"rawSearch": raw_search}, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Only exact matches: data["additionalSearch"] holds the region-wide
        # remote padding this rewrite exists to avoid.
        postings = data.get("postings", [])
        return postings if isinstance(postings, list) else []

    def _categories_for_roles(self, roles: list[str]) -> list[str]:
        categories = []
        for role in roles:
            normalized = normalize_text(role)
            for category, terms in CATEGORY_TERMS.items():
                if any(term in normalized for term in terms):
                    categories.append(category)
        return sorted(set(categories or ["devops"]))

    def _parse_posting(self, posting: dict, config: AppConfig) -> JobPosting | None:
        title = str(posting.get("title") or "").strip()
        slug = str(posting.get("url") or "").strip()
        if not title or not slug:
            return None

        skills = self._skills(posting)
        matched_role = match_role(f"{title} {' '.join(skills)}", config.roles)
        if not matched_role:
            return None

        czech_places, remote = self._czech_places(posting)
        if not czech_places:
            # No Czech office at all: a remote posting here is the Polish
            # spillover this source must not report.
            return None

        location = ", ".join(czech_places)
        match = district_match(location, config.include_unspecified_prague)
        if not match and remote:
            location = f"{location} / remote"
            match = "Remote"
        if not match:
            return None

        company = str(posting.get("name") or "").strip()
        salary = self._salary(posting)
        summary_parts = [part for part in [salary, ", ".join(skills)] if part]

        return JobPosting(
            source=self.name,
            source_id=slug,
            title=title,
            company=company,
            url=f"{self.base_url}/cz/job/{slug}",
            location=location,
            district_match=match,
            posted_date=self._posted_date(posting),
            company_description=" | ".join(summary_parts),
            summary=" | ".join(summary_parts),
            matched_query=matched_role,
        )

    def _czech_places(self, posting: dict) -> tuple[list[str], bool]:
        """Czech place names plus whether the posting is offered remotely.

        Postings list every office; a remote job of a Warsaw company has
        only POL places and must not appear in a Prague report.
        """
        places = (posting.get("location") or {}).get("places") or []
        czech: list[str] = []
        remote = bool(posting.get("fullyRemote"))
        for place in places:
            if not isinstance(place, dict):
                continue
            city = str(place.get("city") or "").strip()
            country = str(((place.get("country") or {}).get("code")) or "").strip().upper()
            if city.lower() == "remote":
                remote = True
                continue
            if country and country != "CZE":
                continue
            if not country and city:
                # No country given: trust only recognizable Czech cities.
                if "praha" not in city.lower() and "prague" not in city.lower():
                    continue
            street = str(place.get("street") or "").strip()
            label = f"{city}, {street}" if street else city
            if city and label not in czech:
                czech.append(label)
        return czech, remote

    def _skills(self, posting: dict) -> list[str]:
        values = []
        technology = str(posting.get("technology") or "").strip()
        if technology:
            values.append(technology)
        tiles = (posting.get("tiles") or {}).get("values") or []
        for tile in tiles:
            value = str((tile or {}).get("value") or "").strip()
            if value and value not in values:
                values.append(value)
        return values[:6]

    def _salary(self, posting: dict) -> str:
        salary = posting.get("salary") or {}
        low, high = salary.get("from"), salary.get("to")
        currency = str(salary.get("currency") or "").strip()
        if not low or not currency:
            return ""
        if high and high != low:
            return f"{low:,.0f}-{high:,.0f} {currency}".replace(",", " ")
        return f"{low:,.0f} {currency}".replace(",", " ")

    def _posted_date(self, posting: dict) -> str:
        timestamp = posting.get("posted")
        if not isinstance(timestamp, (int, float)) or timestamp <= 0:
            return ""
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()
