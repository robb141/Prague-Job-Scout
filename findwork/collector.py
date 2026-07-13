from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

from .config import load_config
from .models import JobPosting
from .output import write_html
from .sources import (
    CocumaSource,
    CompanyPagesSource,
    JenPraceSource,
    JobsCzSource,
    LinkedInSource,
    NoFluffJobsSource,
    PraceCzSource,
    StartupJobsSource,
)
from .sources.base import JobSource
from .state import load_state, save_state


logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]

SOURCE_CLASSES: dict[str, type[JobSource]] = {
    "jobs_cz": JobsCzSource,
    "prace_cz": PraceCzSource,
    "linkedin": LinkedInSource,
    "nofluffjobs": NoFluffJobsSource,
    "startupjobs": StartupJobsSource,
    "jenprace": JenPraceSource,
    "cocuma": CocumaSource,
    "company_pages": CompanyPagesSource,
}


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

    sources = [
        source_class()
        for key, source_class in SOURCE_CLASSES.items()
        if config.sources.get(key, {}).get("enabled", True)
    ]

    collected: dict[str, JobPosting] = {}
    with ThreadPoolExecutor(max_workers=len(sources) or 1) as executor:
        futures = [executor.submit(source.fetch, config) for source in sources]
        # Iterate in submission order so deduplication priority between
        # sources stays deterministic.
        for source, future in zip(sources, futures):
            try:
                source_jobs = future.result()
            except Exception:
                logger.exception("Source %s failed", source.name)
                continue
            logger.info("%s: %d jobs", source.name, len(source_jobs))
            for job in source_jobs:
                collected.setdefault(job.stable_id, job)

    state_path = data_dir / "state.json"
    state = load_state(state_path)

    jobs = [replace(job, is_new=job.stable_id not in state.seen) for job in collected.values()]
    jobs.sort(key=lambda item: (not item.is_new, item.company.lower(), item.title.lower()))

    html_path = output_dir / "index.html"

    write_html(html_path, jobs, config, state.last_run_at)
    save_state(state_path, state, jobs)

    return CollectSummary(
        total=len(jobs),
        new=sum(1 for job in jobs if job.is_new),
        html_path=html_path,
    )
