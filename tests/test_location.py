from findwork.location import district_match, normalize_text


def test_normalize_text_collapses_whitespace_and_lowercases():
    assert normalize_text("  Praha\n 8 &amp; Karlín ") == "praha 8 & karlín"


def test_district_from_number():
    assert district_match("Praha 8 - Karlín", True) == "Praha 8"
    assert district_match("Prague 7", True) == "Praha 7"
    assert district_match("Praha 10", True) == "Praha 10"


def test_district_from_neighborhood_name():
    assert district_match("Praha – Michle", True) == "Praha 4"
    assert district_match("Praha – Chodov", True) == "Praha 11"
    assert district_match("Praha – Nové Město", True) == "Praha 1"
    assert district_match("Praha – Stodůlky", True) == "Praha 13"
    assert district_match("Praha – Horní Počernice", True) == "Praha 20"
    assert district_match("Karlín, Praha", True) == "Praha 8"


def test_explicit_district_number_beats_neighborhood():
    assert district_match("Praha 8 - Karlín", True) == "Praha 8"


def test_neighborhood_without_prague_mention_is_ignored():
    assert district_match("Karlin office", True) is None


def test_same_named_towns_elsewhere_are_not_districts():
    assert district_match("Nové Město na Moravě, dojezd do Prahy? Praha", True) == "Praha, district not specified"


def test_unknown_neighborhood_falls_back_to_unspecified():
    assert district_match("Kancelář v Holešovicích, Praha", True) == "Praha, district not specified"


def test_unspecified_prague_respects_flag():
    assert district_match("Praha", True) == "Praha, district not specified"
    assert district_match("Praha", False) is None


def test_non_prague_returns_none():
    assert district_match("Brno", True) is None
    assert district_match("", True) is None


def test_district_number_out_of_range_falls_back():
    assert district_match("Praha 99", True) == "Praha, district not specified"
    assert district_match("Praha 99", False) is None
