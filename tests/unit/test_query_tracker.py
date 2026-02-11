"""Unit tests for query tracker storage and pruning behavior."""

from datetime import datetime, timedelta

from src.api import query_tracker


def test_query_tracker_create_update_get_roundtrip():
    query_tracker.reset_query_status_for_tests()

    query_tracker.create_query_status(
        query_id="q1",
        query_text="Analyze AAPL",
        status="accepted",
        progress=0.0,
    )
    query_tracker.update_query_status(
        query_id="q1",
        status="completed",
        progress=1.0,
        metadata={"answer": "ok"},
    )
    entry = query_tracker.get_query_status("q1")

    assert entry is not None
    assert entry["status"] == "completed"
    assert entry["progress"] == 1.0
    assert entry["metadata"]["answer"] == "ok"


def test_query_tracker_prunes_expired_entries(monkeypatch):
    query_tracker.reset_query_status_for_tests()
    monkeypatch.setenv("QUERY_TRACKER_TTL_HOURS", "1")

    old = query_tracker.create_query_status(
        query_id="old-q",
        query_text="old",
        status="completed",
        progress=1.0,
    )
    old["updated_at"] = (datetime.utcnow() - timedelta(hours=5)).isoformat()

    query_tracker.create_query_status(
        query_id="new-q",
        query_text="new",
        status="accepted",
        progress=0.0,
    )

    assert query_tracker.get_query_status("old-q") is None
    assert query_tracker.get_query_status("new-q") is not None


def test_query_tracker_prunes_overflow_entries(monkeypatch):
    query_tracker.reset_query_status_for_tests()
    monkeypatch.setenv("QUERY_TRACKER_TTL_HOURS", "24")
    monkeypatch.setenv("QUERY_TRACKER_MAX_ENTRIES", "100")

    # Create more than max entries.
    for idx in range(130):
        query_tracker.create_query_status(
            query_id=f"q-{idx}",
            query_text=f"query {idx}",
            status="accepted",
            progress=0.0,
        )

    # Oldest entries should be pruned.
    assert query_tracker.get_query_status("q-0") is None
    # Newest entries should remain.
    assert query_tracker.get_query_status("q-129") is not None


def test_query_tracker_filters_by_state_and_query_text():
    query_tracker.reset_query_status_for_tests()
    query_tracker.create_query_status(query_id="q1", query_text="Analyze AAPL", status="completed")
    query_tracker.create_query_status(query_id="q2", query_text="Analyze TSLA", status="failed")
    query_tracker.create_query_status(query_id="q3", query_text="Risk model for AAPL", status="completed")

    completed = query_tracker.list_query_statuses(limit=10, state="completed")
    assert len(completed) == 2
    assert all(row["status"] == "completed" for row in completed)

    aapl_only = query_tracker.list_query_statuses(limit=10, query_contains="aapl")
    assert len(aapl_only) == 2
    assert all("aapl" in row["query_text"].lower() for row in aapl_only)
