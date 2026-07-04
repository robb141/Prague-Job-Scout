from __future__ import annotations

import re
import time
from html import unescape
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from findwork.config import AppConfig
from findwork.location import district_match, normalize_text
from findwork.models import JobPosting
from findwork.sources.base import JobSource


class NoFluffJobsSource(JobSource):
    name = "nofluffjobs"
    base_url = "https://nofluffjobs.com"

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
        categories = self._categories_for_roles(config.roles)

        for category in categories:
            url = f"{self.base_url}/cz/jobs/{quote(category)}?criteria=city%3Dpraha"
            response = self._get_with_retry(url)

            for job in self._parse_page(response.text, category, config):
                jobs.setdefault(job.stable_id, job)

            time.sleep(config.request_delay_seconds)

        return list(jobs.values())

    def _get_with_retry(self, url: str) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        raise last_error or RuntimeError(f"Failed to fetch {url}")

    def _categories_for_roles(self, roles: list[str]) -> list[str]:
        categories = []
        for role in roles:
            normalized = normalize_text(role)
            if any(term in normalized for term in ["devops", "sre", "site reliability", "kubernetes", "platform"]):
                categories.append("devops")
            if any(term in normalized for term in ["cloud", "aws", "azure", "gcp"]):
                categories.append("devops")
        return sorted(set(categories or ["devops"]))

    def _parse_page(self, html: str, matched_query: str, config: AppConfig) -> list[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("a.posting-list-item, [nfj-postings-item]")
        jobs = []

        for card in cards:
            job = self._parse_card(card, matched_query, config)
            if job:
                jobs.append(job)

        return jobs

    def _parse_card(self, card: Tag, matched_query: str, config: AppConfig) -> JobPosting | None:
        href = str(card.get("href") or "")
        title = self._clean_title(self._text(card.select_one(".posting-title__position, h3")))
        company = self._text(card.select_one("h4"))
        full_text = self._text(card)
        location = self._location_from_text(full_text, company)

        if not title or not href:
            return None
        if "praha" not in normalize_text(location):
            return None

        match = district_match(location, include_unspecified_prague=True)
        if not match:
            return None

        url = urljoin(self.base_url, href)
        source_id = href.strip("/").split("/")[-1]
        skills = self._skills_from_card(card)
        salary = self._salary_from_text(full_text)
        summary_parts = [part for part in [salary, ", ".join(skills), company] if part]

        return JobPosting(
            source=self.name,
            source_id=source_id,
            title=title,
            company=company,
            url=url,
            location=location,
            district_match=match,
            posted_date=self._posted_date(full_text),
            company_description=" | ".join(summary_parts),
            summary=" | ".join(summary_parts),
            matched_query=matched_query,
        )

    def _location_from_text(self, text: str, company: str) -> str:
        if "Praha" not in text:
            return ""
        after_company = text.split(company, 1)[-1] if company and company in text else text
        found = re.search(r"(Praha(?:\s*[0-9])?(?:\s*[–-]\s*[\wÁ-ž]+)?)", after_company)
        return found.group(1).strip() if found else "Praha"

    def _skills_from_card(self, card: Tag) -> list[str]:
        values = []
        for node in card.select("[class*='tw-rounded'], common-posting-item-tag, nfj-posting-item-tag"):
            text = self._text(node)
            if text and 2 <= len(text) <= 40 and not re.search(r"\d+k|CZK|NEW", text):
                values.append(text)
        return list(dict.fromkeys(values))[:6]

    def _salary_from_text(self, text: str) -> str:
        found = re.search(r"(\d+(?:\.\d+)?k(?:\s*[–+-]\s*\d+(?:\.\d+)?k)?\s*CZK)", text)
        return found.group(1) if found else ""

    def _posted_date(self, text: str) -> str:
        if re.search(r"\bNEW\b", text):
            return "NEW"
        return ""

    def _clean_title(self, value: str) -> str:
        return re.sub(r"\s+NEW$", "", value).strip()

    def _text(self, node: Tag | None) -> str:
        if not node:
            return ""
        return re.sub(r"\s+", " ", unescape(node.get_text(" ", strip=True))).strip()
