from __future__ import annotations

import re
import time
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup, Tag

from findwork.config import AppConfig
from findwork.location import district_match, strip_diacritics
from findwork.models import JobPosting
from findwork.roles import match_role
from findwork.sources.base import JobSource


class PraceCzSource(JobSource):
    name = "prace.cz"
    base_url = "https://www.prace.cz"

    def fetch(self, config: AppConfig) -> list[JobPosting]:
        jobs: dict[str, JobPosting] = {}
        for role in config.roles:
            for page in range(1, config.max_pages_per_query + 1):
                params = {"q[]": role}
                if page > 1:
                    params["page"] = str(page)
                url = f"{self.base_url}/nabidky/praha/?{urlencode(params)}"
                response = self._get(url)
                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.select("article[id^='advert-']")
                if not cards:
                    break

                for card in cards:
                    job = self._parse_card(card, role, config)
                    if job:
                        jobs.setdefault(job.stable_id, job)

                time.sleep(config.request_delay_seconds)

        return list(jobs.values())

    def _parse_card(self, card: Tag, role: str, config: AppConfig) -> JobPosting | None:
        link = card.select_one("[data-testid='advert-link']")
        if not link:
            return None

        title = self._text(link)
        href = str(link.get("href") or "")
        if not title or not href:
            return None

        fields = self._labeled_fields(card)
        company = fields.get("nazev firmy", "") or self._attr(card.select_one("img[alt]"), "alt")
        location = fields.get("lokalita", "")
        card_text = self._text(card)

        # General board; the search returns loosely related ads too.
        if not match_role(f"{title} {card_text}", config.roles):
            return None

        match = district_match(f"{location} {card_text}", config.include_unspecified_prague)
        if not match:
            return None

        extras = [value for key, value in fields.items() if key not in {"nazev firmy", "lokalita"}]
        summary = " | ".join(dict.fromkeys(part for part in [*extras, company] if part))[:300]

        return JobPosting(
            source=self.name,
            source_id=self._source_id(card, href),
            title=title,
            company=company,
            url=urljoin(self.base_url, href).split("?")[0],
            location=location,
            district_match=match,
            posted_date="",
            company_description=summary,
            summary=summary,
            matched_query=role,
        )

    def _labeled_fields(self, card: Tag) -> dict[str, str]:
        """Cards label values with visually hidden spans ("Lokalita:", ...)."""
        fields: dict[str, str] = {}
        for hidden in card.select(".accessibility-hidden"):
            label = _ascii_key(self._text(hidden))
            item = hidden.parent
            if not label or item is None:
                continue
            value = self._text(item).replace(self._text(hidden), "", 1).strip(" :")
            if value:
                fields.setdefault(label, value)
        return fields

    def _source_id(self, card: Tag, href: str) -> str:
        card_id = str(card.get("id") or "")
        if card_id.startswith("advert-"):
            return card_id.removeprefix("advert-")
        found = re.search(r"/nabidka/([0-9a-f-]+)/", href)
        return found.group(1) if found else href


def _ascii_key(value: str) -> str:
    return strip_diacritics(value).strip(" :").lower()
