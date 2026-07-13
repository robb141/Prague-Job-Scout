from __future__ import annotations

import re

from .location import normalize_text


# Words that describe seniority or the job itself rather than the specialty.
# "Python developer" should match any posting mentioning Python, not only
# postings that also contain the word "developer".
GENERIC_WORDS = {
    "admin",
    "administrator",
    "developer",
    "engineer",
    "expert",
    "junior",
    "lead",
    "senior",
    "specialist",
}


def role_terms(roles: list[str]) -> list[tuple[str, str]]:
    """Map each configured role to its distinctive search term.

    Returns (term, role) pairs sorted longest-term-first so that more
    specific terms ("site reliability") win over shorter ones ("sre").
    """
    terms: dict[str, str] = {}
    for role in roles:
        normalized = normalize_text(role)
        words = [word for word in normalized.split() if word not in GENERIC_WORDS]
        term = " ".join(words) or normalized
        terms.setdefault(term, role)
    return sorted(terms.items(), key=lambda item: len(item[0]), reverse=True)


def match_role(text: str, roles: list[str]) -> str:
    """Return the configured role whose term appears in text, or ""."""
    normalized = normalize_text(text)
    for term, role in role_terms(roles):
        if re.search(rf"\b{re.escape(term)}\b", normalized):
            return role
    return ""
