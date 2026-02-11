"""In-memory query status tracking for async API workflow."""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any, Dict, Optional
import os


_lock = Lock()
_query_status: Dict[str, Dict[str, Any]] = {}


def _ttl_hours() -> int:
    try:
        return max(int(os.getenv("QUERY_TRACKER_TTL_HOURS", "24")), 1)
    except Exception:
        return 24


def _max_entries() -> int:
    try:
        return max(int(os.getenv("QUERY_TRACKER_MAX_ENTRIES", "5000")), 100)
    except Exception:
        return 5000


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


def _parse_iso(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None


def _prune_locked() -> None:
    if not _query_status:
        return

    now = datetime.utcnow()
    ttl = _ttl_hours()

    expired_keys = []
    for query_id, payload in _query_status.items():
        updated_at = _parse_iso(payload.get("updated_at"))
        if updated_at is None:
            continue
        age_hours = (now - updated_at).total_seconds() / 3600.0
        if age_hours > ttl:
            expired_keys.append(query_id)
    for key in expired_keys:
        _query_status.pop(key, None)

    max_count = _max_entries()
    if len(_query_status) <= max_count:
        return

    # Keep newest entries by updated_at, drop oldest overflow.
    sortable = []
    for query_id, payload in _query_status.items():
        ts = _parse_iso(payload.get("updated_at")) or datetime.min
        sortable.append((ts, query_id))
    sortable.sort(key=lambda item: item[0], reverse=True)
    keep = {query_id for _, query_id in sortable[:max_count]}
    for query_id in list(_query_status.keys()):
        if query_id not in keep:
            _query_status.pop(query_id, None)


def create_query_status(
    query_id: str,
    query_text: str,
    status: str = "accepted",
    current_node: Optional[str] = None,
    progress: float = 0.0,
    verified_facts_count: int = 0,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = _utcnow_iso()
    payload = {
        "query_id": query_id,
        "query_text": query_text,
        "status": status,
        "current_node": current_node,
        "progress": float(progress),
        "verified_facts_count": int(verified_facts_count),
        "error": error,
        "created_at": now,
        "updated_at": now,
        "metadata": metadata or {},
    }
    with _lock:
        _prune_locked()
        _query_status[query_id] = payload
    return payload


def update_query_status(
    query_id: str,
    status: Optional[str] = None,
    current_node: Optional[str] = None,
    progress: Optional[float] = None,
    verified_facts_count: Optional[int] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    query_text: Optional[str] = None,
) -> Dict[str, Any]:
    with _lock:
        _prune_locked()
        existing = _query_status.get(query_id)
        if existing is None:
            now = _utcnow_iso()
            existing = {
                "query_id": query_id,
                "query_text": query_text or "",
                "status": status or "processing",
                "current_node": current_node,
                "progress": float(progress if progress is not None else 0.0),
                "verified_facts_count": int(verified_facts_count or 0),
                "error": error,
                "created_at": now,
                "updated_at": now,
                "metadata": metadata or {},
            }
            _query_status[query_id] = existing
            return existing

        if status is not None:
            existing["status"] = status
        if current_node is not None:
            existing["current_node"] = current_node
        if progress is not None:
            existing["progress"] = float(progress)
        if verified_facts_count is not None:
            existing["verified_facts_count"] = int(verified_facts_count)
        if error is not None:
            existing["error"] = error
        if metadata:
            existing["metadata"] = {**existing.get("metadata", {}), **metadata}
        if query_text is not None:
            existing["query_text"] = query_text
        existing["updated_at"] = _utcnow_iso()
        return existing


def get_query_status(query_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        _prune_locked()
        payload = _query_status.get(query_id)
        if not payload:
            return None
        return dict(payload)


def list_query_statuses(
    limit: int = 20,
    state: Optional[str] = None,
    query_contains: Optional[str] = None,
) -> list[Dict[str, Any]]:
    with _lock:
        _prune_locked()
        rows = [dict(value) for value in _query_status.values()]

    if state:
        normalized_state = state.strip().lower()
        rows = [row for row in rows if str(row.get("status", "")).lower() == normalized_state]

    if query_contains:
        token = query_contains.strip().lower()
        rows = [
            row
            for row in rows
            if token in str(row.get("query_text", "")).lower()
        ]

    def _sort_key(item: Dict[str, Any]) -> datetime:
        return _parse_iso(item.get("updated_at")) or datetime.min

    rows.sort(key=_sort_key, reverse=True)
    return rows[: max(limit, 1)]


def reset_query_status_for_tests() -> None:
    with _lock:
        _query_status.clear()
