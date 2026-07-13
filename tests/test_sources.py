from bs4 import BeautifulSoup

from findwork.config import AppConfig
from findwork.sources.company_pages import CompanyPagesSource
from findwork.sources.jenprace import JenPraceSource
from findwork.sources.nofluffjobs import NoFluffJobsSource


def make_config(**overrides) -> AppConfig:
    defaults = dict(
        roles=["DevOps engineer", "Python developer", "Data engineer"],
        include_unspecified_prague=True,
        max_pages_per_query=1,
        request_delay_seconds=0.0,
        sources={},
    )
    defaults.update(overrides)
    return AppConfig(**defaults)


def test_nofluffjobs_categories_cover_backend_and_data():
    source = NoFluffJobsSource()
    categories = source._categories_for_roles(["DevOps engineer", "Python developer", "Data engineer"])
    assert categories == ["backend", "data", "devops"]


def test_nofluffjobs_categories_default_to_devops():
    source = NoFluffJobsSource()
    assert source._categories_for_roles(["Accountant"]) == ["devops"]


def nfj_posting(**overrides) -> dict:
    posting = {
        "title": "DevOps/SRE Engineer",
        "name": "Ework Group",
        "url": "devops-sre-engineer-ework-group-remote",
        "fullyRemote": False,
        "posted": 1783685514457,
        "salary": {"from": 122100, "to": 150600, "currency": "CZK"},
        "technology": "Python",
        "tiles": {"values": [{"value": "K8s", "type": "requirement"}]},
        "location": {
            "places": [
                {"city": "Remote"},
                {"city": "Warsaw", "country": {"code": "POL", "name": "Poland"}},
                {"country": {"code": "POL", "name": "Poland"}},
            ]
        },
    }
    posting.update(overrides)
    return posting


def test_nofluffjobs_drops_polish_remote_postings():
    # The exact case reported: remote posting whose only offices are in Poland.
    job = NoFluffJobsSource()._parse_posting(nfj_posting(), make_config())
    assert job is None


def test_nofluffjobs_keeps_prague_postings():
    posting = nfj_posting(
        location={"places": [{"city": "Prague", "country": {"code": "CZE"}}, {"city": "Remote"}]},
    )
    job = NoFluffJobsSource()._parse_posting(posting, make_config())
    assert job is not None
    assert job.district_match == "Praha, district not specified"
    assert job.posted_date == "2026-07-10"
    assert "122 100" in job.summary
    assert job.url == "https://nofluffjobs.com/cz/job/devops-sre-engineer-ework-group-remote"


def test_nofluffjobs_czech_remote_becomes_remote():
    posting = nfj_posting(
        location={"places": [{"city": "Brno", "country": {"code": "CZE"}}, {"city": "Remote"}]},
    )
    job = NoFluffJobsSource()._parse_posting(posting, make_config())
    assert job is not None
    assert job.district_match == "Remote"
    assert job.location == "Brno / remote"


def test_nofluffjobs_czech_office_street_resolves_district():
    posting = nfj_posting(
        location={"places": [{"city": "Praha", "street": "Rohanské nábřeží, Karlín", "country": {"code": "CZE"}}]},
    )
    job = NoFluffJobsSource()._parse_posting(posting, make_config())
    assert job is not None
    assert job.district_match == "Praha 8"


def test_jenprace_dedupe_repeated():
    source = JenPraceSource()
    assert source._dedupe_repeated("Acme s.r.o. | Acme s.r.o.") == "Acme s.r.o."
    assert source._dedupe_repeated("Praha 8 Praha 8") == "Praha 8"
    assert source._dedupe_repeated("Praha 8") == "Praha 8"


def test_company_pages_respects_unspecified_prague_flag():
    html = """
    <div><a href="/jobs/devops">DevOps Engineer – Praha</a></div>
    """
    source = CompanyPagesSource()

    included = source._parse_page(html, "https://example.com", "Example", "", make_config())
    assert included[0].district_match == "Praha, district not specified"

    excluded = source._parse_page(
        html, "https://example.com", "Example", "", make_config(include_unspecified_prague=False)
    )
    assert excluded[0].district_match == ""


def test_company_pages_nearby_text_stops_before_whole_page():
    html = "<body><main>" + "x" * 500 + "<section><div><a href='/j'>DevOps</a></div></section></main></body>"
    soup = BeautifulSoup(html, "html.parser")
    link = soup.find("a")
    nearby = CompanyPagesSource()._nearby_text(link)
    assert "x" * 50 not in nearby
    assert "DevOps" in nearby
