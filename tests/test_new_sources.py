from bs4 import BeautifulSoup

from findwork.config import AppConfig
from findwork.sources.linkedin import LinkedInSource
from findwork.sources.prace_cz import PraceCzSource


def make_config(**overrides) -> AppConfig:
    defaults = dict(
        roles=["DevOps engineer", "Python developer", "Cloud engineer"],
        include_unspecified_prague=True,
        max_pages_per_query=1,
        request_delay_seconds=0.0,
        sources={},
    )
    defaults.update(overrides)
    return AppConfig(**defaults)


LINKEDIN_CARD = """
<div class="base-card" data-entity-urn="urn:li:jobPosting:4123456789">
  <a class="base-card__full-link" href="https://cz.linkedin.com/jobs/view/devops-engineer-at-acme-4123456789?refId=abc&trackingId=def">DevOps Engineer</a>
  <div class="base-search-card__info">
    <h3 class="base-search-card__title">DevOps Engineer</h3>
    <h4 class="base-search-card__subtitle"><a>Acme s.r.o.</a></h4>
    <span class="job-search-card__location">Prague 9, Prague, Czechia</span>
    <time datetime="2026-07-06">1 week ago</time>
  </div>
</div>
"""


def parse_linkedin(html: str, config: AppConfig):
    card = BeautifulSoup(html, "html.parser").select_one(".base-card")
    return LinkedInSource()._parse_card(card, config)


def test_linkedin_card_parses():
    job = parse_linkedin(LINKEDIN_CARD, make_config())
    assert job is not None
    assert job.source_id == "4123456789"
    assert job.title == "DevOps Engineer"
    assert job.company == "Acme s.r.o."
    assert job.district_match == "Praha 9"
    assert job.posted_date == "2026-07-06"
    assert "?" not in job.url  # tracking params stripped


def test_linkedin_drops_unrelated_titles():
    html = LINKEDIN_CARD.replace("DevOps Engineer", "Accountant")
    assert parse_linkedin(html, make_config()) is None


def test_linkedin_drops_non_prague():
    html = LINKEDIN_CARD.replace("Prague 9, Prague, Czechia", "Brno, Czechia")
    assert parse_linkedin(html, make_config()) is None


PRACE_CZ_CARD = """
<article class="JobCard" id="advert-9473b8e9-5b93-49b0-b1a9-e1c2240b5411">
  <h2 data-testid="job-card-title">
    <a data-testid="advert-link" href="/nabidka/9473b8e9-5b93-49b0-b1a9-e1c2240b5411/?rps=2077">DevOps Engineer (Mid-Senior)</a>
  </h2>
  <ul>
    <li><span class="accessibility-hidden">Lokalita:</span><span>Praha-Karlín</span></li>
    <li><span class="accessibility-hidden">Název firmy:</span><span>Firma XY a.s.</span></li>
    <li><span class="accessibility-hidden">Plat:</span><span>80 000 Kč</span></li>
  </ul>
</article>
"""


def parse_prace(html: str, config: AppConfig):
    card = BeautifulSoup(html, "html.parser").select_one("article")
    return PraceCzSource()._parse_card(card, "DevOps engineer", config)


def test_prace_cz_card_parses():
    job = parse_prace(PRACE_CZ_CARD, make_config())
    assert job is not None
    assert job.source_id == "9473b8e9-5b93-49b0-b1a9-e1c2240b5411"
    assert job.company == "Firma XY a.s."
    assert job.location == "Praha-Karlín"
    assert job.district_match == "Praha 8"
    assert "80 000 Kč" in job.summary
    assert job.url == "https://www.prace.cz/nabidka/9473b8e9-5b93-49b0-b1a9-e1c2240b5411/"


def test_prace_cz_drops_unrelated_ads():
    html = PRACE_CZ_CARD.replace("DevOps Engineer (Mid-Senior)", "Řidič skupiny B")
    assert parse_prace(html, make_config()) is None
