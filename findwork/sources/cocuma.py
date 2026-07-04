from __future__ import annotations

import re
import time
from html import unescape
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from findwork.config import AppConfig
from findwork.location import district_match, normalize_text
from findwork.models import JobPosting
from findwork.sources.base import JobSource


class CocumaSource(JobSource):
    name = "cocuma"
    base_url = "https://www.cocuma.cz"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
                ),
                "Accept-Language": "cs,en;q=0.8",
            }
        )

    def fetch(self, config: AppConfig) -> list[JobPosting]:
        jobs: dict[str, JobPosting] = {}
        for role in config.roles:
            query = quote_plus(role)
            for page in range(1, config.max_pages_per_query + 1):
                path = "/jobs/" if page == 1 else f"/jobs/page/{page}/"
                url = f"{self.base_url}{path}?search={query}"
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.select("a.job-thumbnail")
                if not cards:
                    break

                for card in cards:
                    job = self._parse_card(card, role, config)
                    if job:
                        jobs.setdefault(job.stable_id, job)

                time.sleep(config.request_delay_seconds)

        return list(jobs.values())

    def _parse_card(self, card: Tag, role: str, config: AppConfig) -> JobPosting | None:
        company = self._text(card.select_one(".job-thumbnail-company"))
        title = self._text(card.select_one(".job-thumbnail-title"))
        city = self._text(card.select_one(".job-thumbnail-city"))
        schedule = self._text(card.select_one(".job-thumbnail-work-shedule"))
        href = str(card.get("href") or "")

        if not title or not href:
            return None

        combined = f"{title} {company} {city} {schedule}"
        if not self._matches_cloud_devops(combined, role):
            return None

        match = self._location_match(city)
        if not match:
            return None

        url = urljoin(self.base_url, href)
        source_id = href.strip("/").split("/")[-1] or url

        return JobPosting(
            source=self.name,
            source_id=source_id,
            title=title,
            company=company,
            url=url,
            location=city,
            district_match=match,
            posted_date="",
            company_description=" | ".join(part for part in [schedule, company] if part),
            summary=" | ".join(part for part in [schedule, company] if part),
            matched_query=role,
        )

    def _location_match(self, city: str) -> str | None:
        normalized = normalize_text(city)
        if any(term in normalized for term in ["remote", "vzdáleně", "vzdaleně", "vzdalene"]):
            return "Remote"
        return district_match(city, include_unspecified_prague=True)

    def _matches_cloud_devops(self, text: str, role: str) -> bool:
        normalized = normalize_text(text)
        terms = [
            "devops",
            "cloud",
            "platform",
            "site reliability",
            "sre",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "linux",
            "infrastructure",
            "infrastrukt",
        ]
        return any(term in normalized for term in terms)

    def _text(self, node: Tag | None) -> str:
        if not node:
            return ""
        return re.sub(r"\s+", " ", unescape(node.get_text(" ", strip=True))).strip()
