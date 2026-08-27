from __future__ import annotations

import unicodedata

# Czech collating order. Each tuple is one "letter" bucket: characters in the
# same bucket share a primary weight and differ only at the secondary (accent)
# level, matching how Czech dictionaries order words. Accented vowels file next
# to their base letter, while č/ř/š/ž are letters in their own right and sort
# immediately after c/r/s/z.
_ALPHABET: tuple[tuple[str, ...], ...] = (
    ("a", "á"),
    ("b",),
    ("c",),
    ("č",),
    ("d", "ď"),
    ("e", "é", "ě"),
    ("f",),
    ("g",),
    ("h",),
    ("i", "í"),
    ("j",),
    ("k",),
    ("l",),
    ("m",),
    ("n", "ň"),
    ("o", "ó"),
    ("p",),
    ("q",),
    ("r",),
    ("ř",),
    ("s",),
    ("š",),
    ("t", "ť"),
    ("u", "ú", "ů"),
    ("v",),
    ("w",),
    ("x",),
    ("y", "ý"),
    ("z",),
    ("ž",),
)

_PRIMARY: dict[str, int] = {}
_SECONDARY: dict[str, int] = {}
for _weight, _group in enumerate(_ALPHABET, start=1):
    for _rank, _char in enumerate(_group):
        _PRIMARY[_char] = _weight
        _SECONDARY[_char] = _rank

# Anything outside the Czech alphabet (digits, punctuation, other scripts)
# sorts after every Czech letter, ordered among itself by code point.
_AFTER = len(_ALPHABET) + 1


def czech_sort_key(text: str) -> tuple[list[int], list[int]]:
    """Sort key that orders strings the way Czech does (č right after c, etc.).

    Case-insensitive. Non-alphabet characters keep a stable order so the
    overall ordering is total.
    """
    text = unicodedata.normalize("NFC", text).casefold()
    primary: list[int] = []
    secondary: list[int] = []
    for char in text:
        if char in _PRIMARY:
            primary.append(_PRIMARY[char])
            secondary.append(_SECONDARY[char])
        else:
            primary.append(_AFTER)
            secondary.append(ord(char))
    return primary, secondary
