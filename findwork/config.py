from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    roles: list[str]
    include_unspecified_prague: bool
    max_pages_per_query: int
    request_delay_seconds: float
    sources: dict[str, dict[str, Any]]


def load_config(path: Path) -> AppConfig:
    with path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    return AppConfig(
        roles=[str(role).strip() for role in data.get("roles", []) if str(role).strip()],
        include_unspecified_prague=bool(data.get("include_unspecified_prague", True)),
        max_pages_per_query=int(data.get("max_pages_per_query", 3)),
        request_delay_seconds=float(data.get("request_delay_seconds", 1.0)),
        sources=data.get("sources", {}),
    )
