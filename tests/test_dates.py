from datetime import date

from findwork.dates import posted_sort_key


TODAY = date(2026, 7, 11)


def test_new_and_today_map_to_today():
    assert posted_sort_key("NEW", TODAY) == "2026-07-11"
    assert posted_sort_key("Zveřejněno dnes", TODAY) == "2026-07-11"


def test_yesterday():
    assert posted_sort_key("včera", TODAY) == "2026-07-10"


def test_iso_date_passthrough():
    assert posted_sort_key("2026-07-01", TODAY) == "2026-07-01"


def test_czech_date():
    assert posted_sort_key("1. 7. 2026", TODAY) == "2026-07-01"
    assert posted_sort_key("11.7.2026", TODAY) == "2026-07-11"


def test_relative_days():
    assert posted_sort_key("před 3 dny", TODAY) == "2026-07-08"
    assert posted_sort_key("3 days ago", TODAY) == "2026-07-08"


def test_relative_weeks_and_hours():
    assert posted_sort_key("před týdnem", TODAY) == "2026-07-04"
    assert posted_sort_key("před 2 hodinami", TODAY) == "2026-07-11"


def test_unknown_is_empty():
    assert posted_sort_key("", TODAY) == ""
    assert posted_sort_key("kdo ví", TODAY) == ""


def test_invalid_calendar_date_is_empty():
    assert posted_sort_key("31. 2. 2026", TODAY) == ""
