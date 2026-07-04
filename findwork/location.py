from __future__ import annotations

import re
from html import unescape


DISTRICT_TERMS = {
    7: [
        "praha 7",
        "prague 7",
        "holešovice",
        "holesovice",
        "letná",
        "letna",
        "bubeneč",
        "bubenec",
    ],
    8: [
        "praha 8",
        "prague 8",
        "karlín",
        "karlin",
        "libeň",
        "liben",
        "kobylisy",
        "bohnice",
        "troja",
        "ďáblice",
        "dablice",
    ],
    9: [
        "praha 9",
        "prague 9",
        "vysočany",
        "vysocany",
        "prosek",
        "letňany",
        "letnany",
        "hloubětín",
        "hloubetin",
        "černý most",
        "cerny most",
    ],
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip().lower()


def district_match(text: str, include_unspecified_prague: bool) -> str | None:
    normalized = normalize_text(text)

    found = re.search(r"\bpra(?:ha|gue)\s*[-.]?\s*(\d{1,2})\b", normalized)
    if found and 1 <= int(found.group(1)) <= 22:
        return f"Praha {int(found.group(1))}"

    for district, terms in DISTRICT_TERMS.items():
        for term in terms:
            if term in normalized:
                return f"Praha {district}"

    if include_unspecified_prague and re.search(r"\bpra(ha|gue)\b", normalized):
        return "Praha, district not specified"

    return None
