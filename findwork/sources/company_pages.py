from __future__ import annotations

import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from findwork.config import AppConfig
from findwork.location import district_match
from findwork.models import JobPosting
from findwork.roles import match_role
from findwork.sources.base import JobSource


class CompanyPagesSource(JobSource):
    name = "company_pages"

    def fetch(self, config: AppConfig) -> list[JobPosting]:
        pages = config.sources.get("company_pages", {}).get("pages") or []
        jobs: dict[str, JobPosting] = {}

        for page in pages:
            company = str(page.get("company", "")).strip()
            url = str(page.get("url", "")).strip()
            default_location = str(page.get("location", "")).strip()
            if not company or not url:
                continue

            response = self._get(url)

            for job in self._parse_page(response.text, url, company, default_location, config):
                jobs.setdefault(job.stable_id, job)

            time.sleep(config.request_delay_seconds)

        return list(jobs.values())

    def _parse_page(
        self,
        html: str,
        page_url: str,
        company: str,
        default_location: str,
        config: AppConfig,
    ) -> list[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        candidates = soup.select("a[href]")
        jobs = []

        for link in candidates:
            text = self._text(link)
            href = str(link.get("href") or "")
            nearby = self._nearby_text(link)
            combined = f"{text} {href} {nearby} {default_location}"
            matched_role = match_role(combined, config.roles)
            if not matched_role:
                continue

            match = district_match(combined, config.include_unspecified_prague)

            jobs.append(
                JobPosting(
                    source=self.name,
                    source_id=urljoin(page_url, href),
                    title=text or matched_role,
                    company=company,
                    url=urljoin(page_url, href),
                    location=self._location(combined) or default_location,
                    district_match=match or "",
                    posted_date="",
                    company_description=self._shorten(nearby),
                    summary=self._shorten(nearby),
                    matched_query=matched_role,
                )
            )

        return jobs

    def _nearby_text(self, link: Tag) -> str:
        # Climb toward the job-listing container, but stop before the
        # container text balloons into whole-page noise.
        node = link
        text = self._text(link)
        for _ in range(3):
            parent = node.parent
            if parent is None or parent.name in {"body", "html", "[document]"}:
                break
            parent_text = self._text(parent)
            if len(parent_text) > 300:
                break
            node = parent
            text = parent_text
        return text

    def _location(self, text: str) -> str:
        found = re.search(r"(Praha(?:\s*[0-9])?(?:\s*[–-]\s*[\wÁ-ž]+)?)", text, flags=re.IGNORECASE)
        return found.group(1) if found else ""

    def _shorten(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()[:300]
