from __future__ import annotations

import re
import time
from html import unescape
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from findwork.config import AppConfig
from findwork.location import district_match, normalize_text
from findwork.models import JobPosting
from findwork.sources.base import JobSource


class JenPraceSource(JobSource):
    name = "jenprace"
    base_url = "https://www.jenprace.cz"

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
            for page in range(1, config.max_pages_per_query + 1):
                params = {"search": role}
                if page > 1:
                    params["page"] = str(page)
                url = f"{self.base_url}/nabidky/praha?{urlencode(params)}"
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.select("article[data-cy^='offer-slug-']")
                if not cards:
                    break

                for card in cards:
                    job = self._parse_card(card, role, config)
                    if job:
                        jobs.setdefault(job.stable_id, job)

                time.sleep(config.request_delay_seconds)

        return list(jobs.values())

    def _parse_card(self, card: Tag, role: str, config: AppConfig) -> JobPosting | None:
        link = card.select_one('[data-cy="offer-link-label"]')
        if not link:
            return None

        title = self._clean_title(self._text(link))
        href = str(link.get("href") or "")
        if not title or not href:
            return None

        company = self._dedupe_repeated(self._text(card.select_one('[data-cy="offer-ownership-company"]')))
        location = self._dedupe_repeated(self._text(card.select_one('[data-cy="offer-locality"]')))
        card_text = self._text(card)
        combined = f"{title} {company} {location} {card_text}"
        if not self._matches_target_role(combined):
            return None

        match = district_match(f"{location} {card_text}", config.include_unspecified_prague)
        if not match:
            return None

        labels = [self._dedupe_repeated(self._text(label)) for label in card.select('[data-cy^="offer-label"]')]
        labels = [label for label in labels if label]
        date = self._text(card.select_one('[data-cy="offer-date-created"]'))
        summary = " | ".join(dict.fromkeys([date, *labels, company]))[:300]
        url = urljoin(self.base_url, href)

        return JobPosting(
            source=self.name,
            source_id=str(card.get("id") or self._source_id(url)),
            title=title,
            company=company,
            url=url,
            location=location,
            district_match=match,
            posted_date=date,
            company_description=summary,
            summary=summary,
            matched_query=role,
        )

    def _matches_target_role(self, text: str) -> bool:
        normalized = normalize_text(text)
        terms = [
            "aws",
            "azure",
            "cloud",
            "data engineer",
            "devops",
            "infrastructure",
            "kubernetes",
            "linux",
            "platform engineer",
            "python",
            "site reliability",
            "sre",
            "terraform",
        ]
        return any(term in normalized for term in terms)

    def _clean_title(self, value: str) -> str:
        return re.sub(r"\s+(TIP|Nutně vás hledají)$", "", value).strip()

    def _dedupe_repeated(self, value: str) -> str:
        parts = [part.strip() for part in re.split(r"\s*\|\s*", value) if part.strip()]
        if parts:
            return parts[0]
        words = value.split()
        half = len(words) // 2
        if half and words[:half] == words[half:]:
            return " ".join(words[:half])
        return value

    def _source_id(self, url: str) -> str:
        found = re.search(r"/nabidka/([^/]+)/", url)
        return found.group(1) if found else url

    def _text(self, node: Tag | None) -> str:
        if not node:
            return ""
        return re.sub(r"\s+", " ", unescape(node.get_text(" ", strip=True))).strip()
