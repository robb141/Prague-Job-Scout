from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import JobPosting


# Ids not seen in any run for this long are dropped so state.json cannot
# grow forever. Long enough that a posting temporarily hidden by a board
# does not come back flagged as NEW.
RETENTION_DAYS = 90


@dataclass
class RunState:
    # stable_id -> ISO timestamp of the last run that saw the posting
    seen: dict[str, str] = field(default_factory=dict)
    last_run_at: str | None = None

    @property
    def seen_ids(self) -> set[str]:
        return set(self.seen)


def load_state(path: Path) -> RunState:
    if not path.exists():
        return RunState()

    with path.open("r", encoding="utf-8") as state_file:
        data = json.load(state_file)

    last_run_at = data.get("last_run_at")
    seen = data.get("seen", {})
    if not isinstance(seen, dict):
        seen = {}

    # Legacy format stored a plain list of ids; treat them as last seen on
    # the previous run so they age out normally.
    legacy_ids = data.get("seen_ids", [])
    if legacy_ids:
        legacy_stamp = last_run_at or datetime.now(timezone.utc).isoformat()
        for job_id in legacy_ids:
            seen.setdefault(job_id, legacy_stamp)

    return RunState(seen=seen, last_run_at=last_run_at)


def save_state(path: Path, state: RunState, jobs: list[JobPosting]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    seen = dict(state.seen)
    for job in jobs:
        seen[job.stable_id] = now_iso

    cutoff = now - timedelta(days=RETENTION_DAYS)
    seen = {job_id: stamp for job_id, stamp in seen.items() if _parse(stamp) >= cutoff}

    payload = {
        "last_run_at": now_iso,
        "seen": {job_id: seen[job_id] for job_id in sorted(seen)},
    }
    with path.open("w", encoding="utf-8") as state_file:
        json.dump(payload, state_file, indent=2, ensure_ascii=False)


def _parse(stamp: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
