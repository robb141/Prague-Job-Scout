from __future__ import annotations

import re
from datetime import date, timedelta

from .location import normalize_text


def posted_sort_key(value: str, today: date | None = None) -> str:
    """Best-effort ISO date for a scraped posted-date string, "" if unknown.

    The boards mix formats ("NEW", "11. 7. 2026", "2026-07-11", "před 3
    dny", "zveřejněno dnes"); this maps them onto sortable ISO dates while
    the report keeps displaying the original text.
    """
    today = today or date.today()
    normalized = normalize_text(value)
    if not normalized:
        return ""

    if re.search(r"\b(new|dnes|today)\b", normalized):
        return today.isoformat()
    if re.search(r"\b(včera|vcera|yesterday)\b", normalized):
        return (today - timedelta(days=1)).isoformat()

    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", normalized)
    if iso:
        return _safe_date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))

    czech = re.search(r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\b", normalized)
    if czech:
        return _safe_date(int(czech.group(3)), int(czech.group(2)), int(czech.group(1)))

    ago = re.search(r"(?:před|pred)\s+(\d+)\s+(dny|dnem|dni|days?)|(\d+)\s+days?\s+ago", normalized)
    if ago:
        days = int(ago.group(1) or ago.group(3))
        return (today - timedelta(days=days)).isoformat()

    weeks = re.search(r"(?:před|pred)\s+(\d+)?\s*(týdnem|týdny|tydnem|tydny)|(\d+)\s+weeks?\s+ago", normalized)
    if weeks:
        count = int(weeks.group(1) or weeks.group(3) or 1)
        return (today - timedelta(weeks=count)).isoformat()

    if re.search(r"(?:před|pred)\s+\d*\s*(hodinou|hodinami|minutou|minutami)|hours?\s+ago", normalized):
        return today.isoformat()

    return ""


def _safe_date(year: int, month: int, day: int) -> str:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""
