import json
from datetime import datetime, timedelta, timezone

from findwork.models import JobPosting
from findwork.state import RETENTION_DAYS, load_state, save_state


def job(source_id: str) -> JobPosting:
    return JobPosting(source="test", source_id=source_id, title="t", company="c", url="u")


def test_missing_file_gives_empty_state(tmp_path):
    state = load_state(tmp_path / "state.json")
    assert state.seen == {}
    assert state.last_run_at is None


def test_roundtrip_marks_jobs_seen(tmp_path):
    path = tmp_path / "state.json"
    save_state(path, load_state(path), [job("a"), job("b")])

    state = load_state(path)
    assert state.seen_ids == {"test:a", "test:b"}
    assert state.last_run_at is not None


def test_legacy_seen_ids_list_is_migrated(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"last_run_at": "2026-07-01T00:00:00+00:00", "seen_ids": ["test:old"]}))

    state = load_state(path)
    assert state.seen == {"test:old": "2026-07-01T00:00:00+00:00"}

    save_state(path, state, [job("new")])
    assert load_state(path).seen_ids == {"test:old", "test:new"}


def test_stale_ids_are_pruned(tmp_path):
    path = tmp_path / "state.json"
    stale = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS + 1)).isoformat()
    fresh = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps({"last_run_at": fresh, "seen": {"test:stale": stale, "test:fresh": fresh}}))

    save_state(path, load_state(path), [])
    assert load_state(path).seen_ids == {"test:fresh"}


def test_current_jobs_refresh_their_timestamp(tmp_path):
    path = tmp_path / "state.json"
    stale = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS + 1)).isoformat()
    path.write_text(json.dumps({"last_run_at": stale, "seen": {"test:a": stale}}))

    save_state(path, load_state(path), [job("a")])
    assert load_state(path).seen_ids == {"test:a"}
