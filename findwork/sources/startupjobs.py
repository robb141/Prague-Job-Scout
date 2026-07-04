from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from findwork.config import AppConfig
from findwork.location import district_match, normalize_text
from findwork.models import JobPosting
from findwork.sources.base import JobSource


class StartupJobsSource(JobSource):
    name = "startupjobs"
    sitemap_url = "https://www.startupjobs.cz/sitemap/offers.xml"

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
        response = self.session.get(self.sitemap_url, timeout=30)
        response.raise_for_status()
        urls = self._matching_offer_urls(response.text, config.roles)

        jobs: dict[str, JobPosting] = {}
        for url, matched_query in urls:
            detail = self.session.get(url, timeout=30)
            detail.raise_for_status()
            job = self._parse_detail(detail.text, url, matched_query, config)
            if job:
                jobs.setdefault(job.stable_id, job)
            time.sleep(config.request_delay_seconds)

        return list(jobs.values())

    def _matching_offer_urls(self, xml_text: str, roles: list[str]) -> list[tuple[str, str]]:
        root = ET.fromstring(xml_text)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        role_terms = self._role_terms(roles)
        matched: list[tuple[str, str]] = []

        for loc in root.findall(".//sm:loc", namespace):
            url = (loc.text or "").strip()
            slug = urlparse(url).path.rsplit("/", 1)[-1]
            normalized_slug = normalize_text(slug.replace("-", " "))
            for term in role_terms:
                if term in normalized_slug:
                    matched.append((url, term))
                    break

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

    def _role_terms(self, roles: list[str]) -> list[str]:
        base_terms = {
            "aws",
            "azure",
            "cloud",
            "data engineer",
            "devops",
            "infrastructure",
            "kubernetes",
            "platform engineer",
            "python",
            "site reliability",
            "sre",
        }
        return sorted({normalize_text(role) for role in roles} | base_terms, key=len, reverse=True)

    def _source_id(self, url: str) -> str:
        found = re.search(r"/nabidka/(\d+)/", url)
        return found.group(1) if found else url

    def _html_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", BeautifulSoup(unescape(value), "html.parser").get_text(" ", strip=True)).strip()

    def _string(self, value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        return ""
