from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from findwork.config import AppConfig
from findwork.location import district_match, normalize_text
from findwork.models import JobPosting
from findwork.roles import match_role
from findwork.sources.base import JobSource


class StartupJobsSource(JobSource):
    name = "startupjobs"
    sitemap_url = "https://www.startupjobs.cz/sitemap/offers.xml"

    def fetch(self, config: AppConfig) -> list[JobPosting]:
        response = self._get(self.sitemap_url)
        urls = self._matching_offer_urls(response.text, config.roles)

        jobs: dict[str, JobPosting] = {}
        for url, matched_query in urls:
            detail = self._get(url)
            job = self._parse_detail(detail.text, url, matched_query, config)
            if job:
                jobs.setdefault(job.stable_id, job)
            time.sleep(config.request_delay_seconds)

        return list(jobs.values())

    def _matching_offer_urls(self, xml_text: str, roles: list[str]) -> list[tuple[str, str]]:
        root = ET.fromstring(xml_text)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        matched: list[tuple[str, str]] = []

        for loc in root.findall(".//sm:loc", namespace):
            url = (loc.text or "").strip()
            slug = urlparse(url).path.rsplit("/", 1)[-1]
            role = match_role(slug.replace("-", " "), roles)
            if role:
                matched.append((url, role))

        return matched

    def _parse_detail(
        self, html: str, url: str, matched_query: str, config: AppConfig
    ) -> JobPosting | None:
        soup = BeautifulSoup(html, "html.parser")
        posting = self._job_posting_json(soup)
        if not posting:
            return None

        location = self._location(posting)
        text = self._posting_text(posting)
        match = district_match(f"{location} {text}", config.include_unspecified_prague)
        if not match:
            return None

        title = self._string(posting.get("title"))
        company_data = posting.get("hiringOrganization") or {}
        company = self._string(company_data.get("name")) if isinstance(company_data, dict) else ""
        company_description = ""
        if isinstance(company_data, dict):
            company_description = self._html_text(self._string(company_data.get("description")))
        summary = self._html_text(self._string(posting.get("description")))[:300]
        source_id = self._source_id(url)

        return JobPosting(
            source=self.name,
            source_id=source_id,
            title=title,
            company=company,
            url=url,
            location=location,
            district_match=match,
            posted_date=self._string(posting.get("datePosted"))[:10],
            company_description=company_description or summary,
            summary=summary,
            matched_query=matched_query,
        )

    def _job_posting_json(self, soup: BeautifulSoup) -> dict | None:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.get_text())
            except json.JSONDecodeError:
                continue
            graph = data.get("@graph", []) if isinstance(data, dict) else []
            for item in graph:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return item
        return None

    def _location(self, posting: dict) -> str:
        candidates = []
        for key in ["jobLocation", "applicantLocationRequirements"]:
            value = posting.get(key)
            values = value if isinstance(value, list) else [value]
            for item in values:
                if isinstance(item, dict):
                    candidates.append(self._string(item.get("name")))
                    address = item.get("address")
                    if isinstance(address, str):
                        candidates.append(address)
                    elif isinstance(address, dict):
                        candidates.append(" ".join(self._string(v) for v in address.values()))
        return ", ".join(dict.fromkeys(part for part in candidates if part))

    def _posting_text(self, posting: dict) -> str:
        parts = [
            self._string(posting.get("title")),
            self._string(posting.get("description")),
            self._location(posting),
        ]
        company = posting.get("hiringOrganization")
        if isinstance(company, dict):
            parts.extend([self._string(company.get("name")), self._string(company.get("description"))])
        return self._html_text(" ".join(parts))

    def _source_id(self, url: str) -> str:
        found = re.search(r"/nabidka/(\d+)/", url)
        return found.group(1) if found else url

    def _html_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", BeautifulSoup(unescape(value), "html.parser").get_text(" ", strip=True)).strip()

    def _string(self, value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        return ""
