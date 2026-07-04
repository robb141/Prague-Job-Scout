from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import load_config
from .models import JobPosting
from .output import write_html
from .sources import (
    CocumaSource,
    CompanyPagesSource,
    JenPraceSource,
    JobsCzSource,
    NoFluffJobsSource,
    StartupJobsSource,
)
from .state import load_state, save_state


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CollectSummary:
    total: int
    new: int
    html_path: Path


def collect_jobs(config_path: Path) -> CollectSummary:
    config = load_config(config_path)
    output_dir = ROOT / "output"
    data_dir = ROOT / "data"
    output_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    sources = []
    if config.sources.get("jobs_cz", {}).get("enabled", True):
        sources.append(JobsCzSource())
    if config.sources.get("nofluffjobs", {}).get("enabled", True):
        sources.append(NoFluffJobsSource())
    if config.sources.get("startupjobs", {}).get("enabled", True):
        sources.append(StartupJobsSource())
    if config.sources.get("jenprace", {}).get("enabled", True):
        sources.append(JenPraceSource())
    if config.sources.get("cocuma", {}).get("enabled", True):
        sources.append(CocumaSource())
    if config.sources.get("company_pages", {}).get("enabled", False):
        sources.append(CompanyPagesSource())

    collected: dict[str, JobPosting] = {}
    for source in sources:
        try:
            source_jobs = source.fetch(config)
        except Exception as exc:
            print(f"Warning: {source.name} failed: {exc}")
            continue
        for job in source_jobs:
            collected.setdefault(job.stable_id, job)

    state_path = data_dir / "state.json"
    state = load_state(state_path)

    jobs = []
    for job in sorted(collected.values(), key=lambda item: (item.is_new, item.company, item.title)):
        jobs.append(
            JobPosting(
                source=job.source,
                source_id=job.source_id,
                title=job.title,
                company=job.company,
                url=job.url,
                location=job.location,
                district_match=job.district_match,
                posted_date=job.posted_date,
                company_description=job.company_description,
                summary=job.summary,
                matched_query=job.matched_query,
                fetched_at=job.fetched_at,
                is_new=job.stable_id not in state.seen_ids,
            )
        )

    jobs.sort(key=lambda item: (not item.is_new, item.company.lower(), item.title.lower()))

    html_path = output_dir / "index.html"

    write_html(html_path, jobs, config, state.last_run_at)
    save_state(state_path, state, jobs)

    return CollectSummary(
        total=len(jobs),
        new=sum(1 for job in jobs if job.is_new),
        html_path=html_path,
    )
