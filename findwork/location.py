from __future__ import annotations

import re
import unicodedata
from html import unescape


# Cadastral areas, municipal parts, and well-known localities mapped to the
# administrative district (Praha 1-22). Job boards usually write
# "Praha – Michle" instead of "Praha 4", so this is what turns neighborhood
# names into district numbers. Keys are lowercase with diacritics stripped;
# areas that span districts get the district holding most of the area.
NEIGHBORHOOD_DISTRICTS: dict[str, int] = {
    # Praha 1
    "stare mesto": 1,
    "josefov": 1,
    "mala strana": 1,
    "hradcany": 1,
    "nove mesto": 1,
    "vaclavske namesti": 1,
    "narodni trida": 1,
    # Praha 2
    "vysehrad": 2,
    "vinohrady": 2,
    "karlovo namesti": 2,
    "albertov": 2,
    # Praha 3
    "zizkov": 3,
    # Praha 4
    "nusle": 4,
    "michle": 4,
    "podoli": 4,
    "branik": 4,
    "krc": 4,
    "lhotka": 4,
    "hodkovicky": 4,
    "kunratice": 4,
    "pankrac": 4,
    "budejovicka": 4,
    "kacerov": 4,
    "brumlovka": 4,
    # Praha 5
    "smichov": 5,
    "andel": 5,
    "kosire": 5,
    "motol": 5,
    "radlice": 5,
    "hlubocepy": 5,
    "jinonice": 5,
    "barrandov": 5,
    "slivenec": 5,
    # Praha 6
    "dejvice": 6,
    "bubenec": 6,
    "stresovice": 6,
    "brevnov": 6,
    "veleslavin": 6,
    "vokovice": 6,
    "liboc": 6,
    "ruzyne": 6,
    "sedlec": 6,
    "petriny": 6,
    "suchdol": 6,
    "nebusice": 6,
    "lysolaje": 6,
    "predni kopanina": 6,
    # Praha 7
    "holesovice": 7,
    "letna": 7,
    "troja": 7,
    # Praha 8
    "karlin": 8,
    "liben": 8,
    "kobylisy": 8,
    "bohnice": 8,
    "cimice": 8,
    "dolni chabry": 8,
    "dablice": 8,
    "brezineves": 8,
    "florenc": 8,
    "palmovka": 8,
    "invalidovna": 8,
    # Praha 9
    "vysocany": 9,
    "prosek": 9,
    "strizkov": 9,
    "hloubetin": 9,
    "hrdlorezy": 9,
    "harfa": 9,
    "ceskomoravska": 9,
    # Praha 10
    "vrsovice": 10,
    "strasnice": 10,
    "malesice": 10,
    "zabehlice": 10,
    "zahradni mesto": 10,
    # Praha 11
    "chodov": 11,
    "haje": 11,
    "opatov": 11,
    "roztyly": 11,
    "seberov": 11,
    # Praha 12
    "modrany": 12,
    "kamyk": 12,
    "komorany": 12,
    "cholupice": 12,
    "tocna": 12,
    "libus": 12,
    # Praha 13
    "stodulky": 13,
    "luziny": 13,
    "nove butovice": 13,
    "trebonice": 13,
    # Praha 14
    "cerny most": 14,
    "kyje": 14,
    "hostavice": 14,
    "dolni pocernice": 14,
    # Praha 15
    "hostivar": 15,
    "horni mecholupy": 15,
    "dolni mecholupy": 15,
    "petrovice": 15,
    "sterboholy": 15,
    "dubec": 15,
    # Praha 16
    "radotin": 16,
    "zbraslav": 16,
    "velka chuchle": 16,
    "lipence": 16,
    "lochkov": 16,
    # Praha 17
    "repy": 17,
    "zlicin": 17,
    # Praha 18
    "letnany": 18,
    "cakovice": 18,
    # Praha 19
    "kbely": 19,
    "vinor": 19,
    "satalice": 19,
    # Praha 20
    "horni pocernice": 20,
    # Praha 21
    "ujezd nad lesy": 21,
    "klanovice": 21,
    "bechovice": 21,
    "kolodeje": 21,
    # Praha 22
    "uhrineves": 22,
    "pitkovice": 22,
    "kralovice": 22,
    "kreslice": 22,
    "kolovraty": 22,
}

# Longest names first so "nove butovice" is tried before shorter overlaps.
# The lookahead rejects same-named towns elsewhere ("Nove Mesto na Morave").
_NEIGHBORHOOD_RE = re.compile(
    r"\b("
    + "|".join(sorted((re.escape(name) for name in NEIGHBORHOOD_DISTRICTS), key=len, reverse=True))
    + r")\b(?!\s+(?:nad|na|pod|u)\b)"
)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip().lower()


def strip_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def district_match(text: str, include_unspecified_prague: bool) -> str | None:
    normalized = strip_diacritics(normalize_text(text))

    found = re.search(r"\bpra(?:ha|gue)\s*[-.]?\s*(\d{1,2})\b", normalized)
    if found and 1 <= int(found.group(1)) <= 22:
        return f"Praha {int(found.group(1))}"

    # Only trust neighborhood names when the text mentions Prague at all;
    # multi-city postings can name similar places elsewhere in the country.
    if re.search(r"\bpra(ha|gue)\b", normalized):
        neighborhood = _NEIGHBORHOOD_RE.search(normalized)
        if neighborhood:
            return f"Praha {NEIGHBORHOOD_DISTRICTS[neighborhood.group(1)]}"
        if include_unspecified_prague:
            return "Praha, district not specified"

    return None
