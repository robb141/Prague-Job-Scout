from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from html import unescape

import requests
from bs4 import Tag

from findwork.config import AppConfig
from findwork.models import JobPosting


logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)


class JobSource(ABC):
    name: str

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "cs,en;q=0.8",
            }
        )

    @abstractmethod
    def fetch(self, config: AppConfig) -> list[JobPosting]:
        raise NotImplementedError

    def _get(self, url: str, timeout: int = 30, attempts: int = 3) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts - 1:
                    delay = 2 * (attempt + 1)
                    logger.warning("%s: retrying %s in %ss (%s)", self.name, url, delay, exc)
                    time.sleep(delay)
        raise last_error or RuntimeError(f"Failed to fetch {url}")

    @staticmethod
    def _text(node: Tag | None) -> str:
        if not node:
            return ""
        return re.sub(r"\s+", " ", unescape(node.get_text(" ", strip=True))).strip()

    @staticmethod
    def _attr(node: Tag | None, name: str) -> str:
        if not node:
            return ""
        return str(node.get(name, "") or "").strip()
