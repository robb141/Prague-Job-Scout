from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import JobPosting


@dataclass
class RunState:
    seen_ids: set[str]
    last_run_at: str | None = None


def load_state(path: Path) -> RunState:
    if not path.exists():
        return RunState(seen_ids=set())

    with path.open("r", encoding="utf-8") as state_file:
        data = json.load(state_file)

    return RunState(
        seen_ids=set(data.get("seen_ids", [])),
        last_run_at=data.get("last_run_at"),
    )


def save_state(path: Path, state: RunState, jobs: list[JobPosting]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    all_ids = state.seen_ids | {job.stable_id for job in jobs}
    payload = {
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "seen_ids": sorted(all_ids),
    }
    with path.open("w", encoding="utf-8") as state_file:
        json.dump(payload, state_file, indent=2, ensure_ascii=False)
