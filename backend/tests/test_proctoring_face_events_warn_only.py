"""
Unit tests for webcam face-detection events being warn-only:
FACE_NOT_DETECTED / MULTIPLE_FACES_DETECTED are logged and deducted from
integrity_score but never increment violation_count or lock the session,
while ordinary violations still escalate to a lock exactly as before.

DB session and Redis are mocked — matches the existing pure-unit-test
convention in this suite (see test_tier_override.py).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from features.proctoring import proctoring_service_async as svc


def _redis_data(count=0, threshold=3, integrity=100):
    return {
        "violation_count": count, "is_locked": False, "integrity_score": integrity,
        "lock_threshold": threshold, "quiz_id": 1, "tenant_id": 1, "participant_id": 1,
    }


def _run(event_type, data, monkeypatch):
    sess = MagicMock(violation_count=data["violation_count"], integrity_score=data["integrity_score"], is_locked=False)
    result = MagicMock()
    result.scalar_one_or_none.return_value = sess
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    monkeypatch.setattr(svc, "_set_redis_session", AsyncMock())
    lock = AsyncMock()
    monkeypatch.setattr(svc, "lock_session", lock)
    resp = asyncio.run(svc._check_escalation("tok", data, "webcam_monitoring", event_type, db, MagicMock()))
    return resp, sess, lock


@pytest.mark.parametrize("event_type,deduction", [("FACE_NOT_DETECTED", 10), ("MULTIPLE_FACES_DETECTED", 15)])
def test_face_event_warns_without_counting_toward_lock(event_type, deduction, monkeypatch):
    data = _redis_data(count=0)
    resp, sess, lock = _run(event_type, data, monkeypatch)
    assert resp.logged is True and resp.is_locked is False
    assert resp.silent is False            # candidate still sees the warning
    assert resp.violations_remaining is None
    assert data["violation_count"] == 0 and sess.violation_count == 0
    assert data["integrity_score"] == 100 - deduction and sess.integrity_score == 100 - deduction
    lock.assert_not_awaited()


def test_face_event_never_locks_even_one_short_of_threshold(monkeypatch):
    data = _redis_data(count=2, threshold=3)
    for _ in range(10):
        resp, _, lock = _run("FACE_NOT_DETECTED", data, monkeypatch)
        assert resp.is_locked is False
        lock.assert_not_awaited()
    assert data["violation_count"] == 2
    assert data["integrity_score"] == 0     # floors at 0, never negative


def test_ordinary_violation_still_counts_and_locks_at_threshold(monkeypatch):
    data = _redis_data(count=1, threshold=3)
    resp, sess, lock = _run("TAB_SWITCH", data, monkeypatch)
    assert resp.is_locked is False and resp.violations_remaining == 1
    assert data["violation_count"] == 2 and sess.violation_count == 2
    lock.assert_not_awaited()

    resp, _, lock = _run("TAB_SWITCH", data, monkeypatch)
    assert resp.is_locked is True and resp.violations_remaining == 0
    lock.assert_awaited_once()


def test_webcam_stream_ended_still_locks_immediately(monkeypatch):
    resp, _, lock = _run("WEBCAM_STREAM_ENDED", _redis_data(), monkeypatch)
    assert resp.is_locked is True
    lock.assert_awaited_once()
