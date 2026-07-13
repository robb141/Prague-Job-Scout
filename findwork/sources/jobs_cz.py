from __future__ import annotations

import re
import time
from urllib.parse import urlencode

from bs4 import BeautifulSoup, Tag

from findwork.config import AppConfig
from findwork.location import district_match, normalize_text
from findwork.models import JobPosting
from findwork.sources.base import JobSource


class JobsCzSource(JobSource):
    name = "jobs.cz"
    base_url = "https://www.jobs.cz/prace/praha/"

    def fetch(self, config: AppConfig) -> list[JobPosting]:
        jobs: dict[str, JobPosting] = {}
        for role in config.roles:
            for page in range(1, config.max_pages_per_query + 1):
                params = {"q": role}
                if page > 1:
                    params["page"] = str(page)
                url = f"{self.base_url}?{urlencode(params)}"
                response = self._get(url)
                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.select(".SearchResultCard")
                if not cards:
                    break

                for card in cards:
                    job = self._parse_card(card, role, config)
                    if job:
                        jobs.setdefault(job.stable_id, job)

                time.sleep(config.request_delay_seconds)

        return list(jobs.values())

    def _parse_card(self, card: Tag, role: str, config: AppConfig) -> JobPosting | None:
        link = card.select_one("a.SearchResultCard__titleLink")
        if not link:
            return None

        title = self._text(link) or self._attr(card, "data-test-ad-title")
        url = self._attr(link, "href")
        source_id = self._attr(link, "data-jobad-id") or self._job_id_from_url(url)

        location = self._text(card.select_one('[data-test="serp-locality"]'))
        card_text = self._text(card)
        match = district_match(f"{location} {card_text}", config.include_unspecified_prague)
        if not match:
            return None

        company = self._company_from_card(card, title)
        posted_date = self._posted_date_from_card(card)
        summary = self._summary_from_card(card, title, company, location)

        return JobPosting(
            source=self.name,
            source_id=source_id,
            title=title,
            company=company,
            url=url,
            location=location,
            district_match=match,
            posted_date=posted_date,
            company_description=summary,
            summary=summary,
            matched_query=role,
        )

    def _company_from_card(self, card: Tag, title: str) -> str:
        company_candidates = [
            '[data-test="serp-company"]',
            ".SearchResultCard__company",
            ".SearchResultCard__body strong",
        ]
        for selector in company_candidates:
            value = self._text(card.select_one(selector))
            if self._looks_like_company(value, title):
                return value

        for item in card.select(".SearchResultCard__footerItem"):
            if item.get("data-test") == "serp-locality":
                continue
            value = self._text(item)
            if self._looks_like_company(value, title):
                return value

        logo = card.select_one("img[alt]")
        if logo and self._attr(logo, "alt"):
            return self._attr(logo, "alt").replace("Logo společnosti", "").strip()

        text_lines = [line.strip() for line in self._text(card).splitlines() if line.strip()]
        for line in text_lines:
            if line != title and "Praha" not in line:
                return line
        return ""

    def _summary_from_card(self, card: Tag, title: str, company: str, location: str) -> str:
        parts = []
        status = self._posted_date_from_card(card)
        if status:
            parts.append(status)

        body = card.select_one(".SearchResultCard__body")
        if body:
            for tag in body.select(".Tag"):
                value = self._text(tag)
                if value and value not in parts:
                    parts.append(value)

        if company:
            parts.append(company)
        return " ".join(parts)[:300]

    def _posted_date_from_card(self, card: Tag) -> str:
        status = self._text(card.select_one(".SearchResultCard__status"))
        if status:
            return status

        text = self._text(card)
        normalized = normalize_text(text)
        patterns = [
            r"zveřejněno\s+([^,.]+)",
            r"přidáno\s+([^,.]+)",
            r"posted\s+([^,.]+)",
            r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})",
        ]
        for pattern in patterns:
            found = re.search(pattern, normalized)
            if found:
                return found.group(1).strip()
        return ""

    def _job_id_from_url(self, url: str) -> str:
        found = re.search(r"/rpd/(\d+)/", url)
        return found.group(1) if found else url

    def _looks_like_company(self, value: str, title: str) -> bool:
        if not value or value == title:
            return False
        normalized = normalize_text(value)
        if "hodnocení na atmoskopu" in normalized:
            return False
        if normalized in {"praha", "brno", "ostrava"}:
            return False
        return True
