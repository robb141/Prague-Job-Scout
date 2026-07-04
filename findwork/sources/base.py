from __future__ import annotations

from abc import ABC, abstractmethod

from findwork.config import AppConfig
from findwork.models import JobPosting


class JobSource(ABC):
    name: str

    @abstractmethod
    def fetch(self, config: AppConfig) -> list[JobPosting]:
        raise NotImplementedError
