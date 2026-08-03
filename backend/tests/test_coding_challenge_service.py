"""
Unit tests for features.coding_challenge.coding_challenge_service_async.
DB session is mocked (fixture ORM objects, not persisted) — matches the existing
pure-unit-test convention in this suite. The real, live restart-resilience check
happens in Phase 10's manual dev-env test, not here.
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from features.coding_challenge import coding_challenge_service_async as svc
from persistence.models.quiz import CodeWorkspace, CodeWorkspaceStatus, CodeSubmission, CodeSubmissionStatus


# ── JWT invite ───────────────────────────────────────────────────────────────

def test_invite_token_round_trip():
    token = svc.create_invite_token(quiz_id=1, question_id=2, candidate_email="Foo@Example.com")
    payload = svc.decode_invite_token(token)
    assert payload["quiz_id"] == 1
    assert payload["question_id"] == 2
    assert payload["candidate_email"] == "foo@example.com"  # lowercased
    assert "jti" in payload and "exp" in payload


def test_decode_invite_token_rejects_expired():
    token = svc.create_invite_token(1, 2, "a@b.com", expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        svc.decode_invite_token(token)
    assert exc_info.value.status_code == 400


def test_decode_invite_token_rejects_garbage():
    with pytest.raises(HTTPException):
        svc.decode_invite_token("not-a-real-token")


def test_decode_invite_token_rejects_missing_claims():
    """A validly-signed token for a *different* purpose (missing our required claims)
    must still be rejected, not silently accepted."""
    from core.security.jwt import create_access_token
    token = create_access_token({"some_other_claim": "x"})
    with pytest.raises(HTTPException):
        svc.decode_invite_token(token)


# ── OTP request/verify ───────────────────────────────────────────────────────

def _fake_redis(increment_return=1, get_json_return=None):
    redis = AsyncMock()
    redis.increment = AsyncMock(return_value=increment_return)
    redis.expire = AsyncMock()
    redis.set_json = AsyncMock()
    redis.get_json = AsyncMock(return_value=get_json_return)
    redis.delete = AsyncMock()
    return redis


def test_request_otp_sends_email_and_stores_in_redis():
    redis = _fake_redis(increment_return=1)
    with patch("core.auth.email_service.send_email", AsyncMock(return_value=True)) as mock_send:
        result = asyncio.run(svc.request_coding_challenge_otp("jti-1", "a@b.com", redis))
    assert result == {"sent": True}
    redis.set_json.assert_called_once()
    key = redis.set_json.call_args[0][0]
    assert key == "coding_challenge_otp:jti-1:a@b.com"
    mock_send.assert_called_once()


def test_request_otp_rate_limited_after_three():
    redis = _fake_redis(increment_return=4)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(svc.request_coding_challenge_otp("jti-1", "a@b.com", redis))
    assert exc_info.value.status_code == 429


def test_request_otp_retries_once_before_failing():
    redis = _fake_redis(increment_return=1)
    send_mock = AsyncMock(side_effect=[False, True])  # fails once, succeeds on retry
    with patch("core.auth.email_service.send_email", send_mock):
        result = asyncio.run(svc.request_coding_challenge_otp("jti-1", "a@b.com", redis))
    assert result == {"sent": True}
    assert send_mock.call_count == 2


def test_request_otp_fails_after_two_failed_attempts():
    redis = _fake_redis(increment_return=1)
    send_mock = AsyncMock(return_value=False)
    with patch("core.auth.email_service.send_email", send_mock):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(svc.request_coding_challenge_otp("jti-1", "a@b.com", redis))
    assert exc_info.value.status_code == 502
    assert send_mock.call_count == 2


def test_verify_otp_correct_code_succeeds_and_deletes():
    redis = _fake_redis(get_json_return={"otp": "123456"})
    result = asyncio.run(svc.verify_coding_challenge_otp("jti-1", "a@b.com", "123456", redis))
    assert result is True
    redis.delete.assert_called_once_with("coding_challenge_otp:jti-1:a@b.com")


def test_verify_otp_wrong_code_fails_without_deleting():
    redis = _fake_redis(get_json_return={"otp": "123456"})
    result = asyncio.run(svc.verify_coding_challenge_otp("jti-1", "a@b.com", "000000", redis))
    assert result is False
    redis.delete.assert_not_called()


def test_verify_otp_missing_or_expired_fails():
    redis = _fake_redis(get_json_return=None)
    result = asyncio.run(svc.verify_coding_challenge_otp("jti-1", "a@b.com", "123456", redis))
    assert result is False


# ── Lifetime-cap job scheduling ─────────────────────────────────────────────

def test_lifetime_cap_job_id_deterministic():
    assert svc.lifetime_cap_job_id("ws-1") == svc.lifetime_cap_job_id("ws-1")
    assert svc.lifetime_cap_job_id("ws-1") != svc.lifetime_cap_job_id("ws-2")


def test_schedule_lifetime_cap_job_calls_scheduler_add_job():
    mock_apscheduler = MagicMock()
    with patch("core.stats.scheduler.scheduler", mock_apscheduler):
        fire_at = datetime.utcnow() + timedelta(seconds=100)
        svc.schedule_lifetime_cap_job(42, "ws-1", fire_at)
    mock_apscheduler.add_job.assert_called_once()
    _, kwargs = mock_apscheduler.add_job.call_args
    assert kwargs["id"] == svc.lifetime_cap_job_id("ws-1")
    assert kwargs["args"] == [42]
    assert kwargs["replace_existing"] is True


def test_schedule_lifetime_cap_job_noop_when_scheduler_not_running():
    with patch("core.stats.scheduler.scheduler", None):
        svc.schedule_lifetime_cap_job(42, "ws-1", datetime.utcnow())  # must not raise


def test_cancel_lifetime_cap_job_calls_remove_job():
    mock_apscheduler = MagicMock()
    with patch("core.stats.scheduler.scheduler", mock_apscheduler):
        svc.cancel_lifetime_cap_job("ws-1")
    mock_apscheduler.remove_job.assert_called_once_with(svc.lifetime_cap_job_id("ws-1"))


def test_cancel_lifetime_cap_job_swallows_missing_job_error():
    mock_apscheduler = MagicMock()
    mock_apscheduler.remove_job.side_effect = Exception("job not found")
    with patch("core.stats.scheduler.scheduler", mock_apscheduler):
        svc.cancel_lifetime_cap_job("ws-1")  # must not raise


# ── reap_abandoned_workspace ─────────────────────────────────────────────────

def _fixture_workspace(status=CodeWorkspaceStatus.ACTIVE, created_at=None) -> CodeWorkspace:
    ws = CodeWorkspace(
        id=1, tenant_id=1, quiz_id=1, question_id=1, candidate_email="a@b.com",
        ide_type="code_server", coder_workspace_name="ws-1", status=status,
        created_at=created_at or datetime.utcnow(),
    )
    return ws


def test_reap_abandoned_workspace_deletes_and_marks_abandoned():
    workspace = _fixture_workspace()
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=workspace)
    mock_db.commit = AsyncMock()
    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("persistence.database_async.AsyncSessionLocal", mock_session_cls), \
         patch.object(svc.coder_client, "delete_workspace", AsyncMock()) as mock_delete:
        asyncio.run(svc.reap_abandoned_workspace(1))

    mock_delete.assert_called_once_with("ws-1")
    assert workspace.status == CodeWorkspaceStatus.ABANDONED
    assert workspace.destroyed_at is not None
    mock_db.commit.assert_called_once()


def test_reap_abandoned_workspace_skips_if_already_submitted():
    """A workspace already submitted before the lifetime cap fired must not be
    force-deleted out from under an in-flight grading job."""
    workspace = _fixture_workspace(status=CodeWorkspaceStatus.SUBMITTED)
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=workspace)
    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("persistence.database_async.AsyncSessionLocal", mock_session_cls), \
         patch.object(svc.coder_client, "delete_workspace", AsyncMock()) as mock_delete:
        asyncio.run(svc.reap_abandoned_workspace(1))

    mock_delete.assert_not_called()
    mock_db.commit.assert_not_called()


def test_reap_abandoned_workspace_marks_abandoned_even_if_delete_fails():
    """Best-effort delete: a failed coder delete must not block marking the DB
    row abandoned (the alternative is a workspace stuck 'active' forever)."""
    workspace = _fixture_workspace()
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=workspace)
    mock_db.commit = AsyncMock()
    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("persistence.database_async.AsyncSessionLocal", mock_session_cls), \
         patch.object(svc.coder_client, "delete_workspace", AsyncMock(side_effect=Exception("boom"))):
        asyncio.run(svc.reap_abandoned_workspace(1))

    assert workspace.status == CodeWorkspaceStatus.ABANDONED
    mock_db.commit.assert_called_once()


def test_reap_abandoned_workspace_noop_if_not_found():
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)
    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("persistence.database_async.AsyncSessionLocal", mock_session_cls):
        asyncio.run(svc.reap_abandoned_workspace(999))  # must not raise


# ── reconcile_on_startup ─────────────────────────────────────────────────────

def _mock_execute_result(rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


def test_reconcile_reschedules_overdue_workspace_immediately():
    overdue_ws = _fixture_workspace(created_at=datetime.utcnow() - timedelta(hours=10))
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _mock_execute_result([overdue_ws]), _mock_execute_result([]), _mock_execute_result([]),
    ])
    mock_db.commit = AsyncMock()

    with patch.object(svc, "schedule_lifetime_cap_job") as mock_schedule:
        summary = asyncio.run(svc.reconcile_on_startup(mock_db))

    assert summary["lifetime_cap_jobs_rescheduled"] == 1
    mock_schedule.assert_called_once()
    _, _, fire_at = mock_schedule.call_args[0]
    assert fire_at <= datetime.utcnow()  # fired immediately, not scheduled for the future


def test_reconcile_reschedules_not_yet_due_workspace_for_remaining_time():
    fresh_ws = _fixture_workspace(created_at=datetime.utcnow())
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _mock_execute_result([fresh_ws]), _mock_execute_result([]), _mock_execute_result([]),
    ])

    with patch.object(svc, "schedule_lifetime_cap_job") as mock_schedule:
        asyncio.run(svc.reconcile_on_startup(mock_db))

    _, _, fire_at = mock_schedule.call_args[0]
    assert fire_at > datetime.utcnow()  # still in the future


def test_reconcile_marks_stuck_provisioning_workspaces_failed():
    """A workspace still PROVISIONING at startup had its background
    provision_workspace_job killed along with the old process (APScheduler jobs
    don't survive a restart) — must be marked provision_failed so it's never
    permanently stuck with nothing for /status to poll toward."""
    stuck1 = _fixture_workspace(status=CodeWorkspaceStatus.PROVISIONING)
    stuck2 = _fixture_workspace(status=CodeWorkspaceStatus.PROVISIONING)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _mock_execute_result([]), _mock_execute_result([stuck1, stuck2]), _mock_execute_result([]),
    ])
    mock_db.commit = AsyncMock()

    summary = asyncio.run(svc.reconcile_on_startup(mock_db))

    assert summary["stuck_provisions_marked_failed"] == 2
    assert stuck1.status == CodeWorkspaceStatus.PROVISION_FAILED
    assert stuck2.status == CodeWorkspaceStatus.PROVISION_FAILED
    mock_db.commit.assert_called()


def test_reconcile_marks_stuck_queued_and_grading_submissions_failed():
    queued = CodeSubmission(id=1, workspace_id=1, question_id=1, status=CodeSubmissionStatus.QUEUED)
    grading = CodeSubmission(id=2, workspace_id=1, question_id=1, status=CodeSubmissionStatus.GRADING)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _mock_execute_result([]), _mock_execute_result([]), _mock_execute_result([queued, grading]),
    ])
    mock_db.commit = AsyncMock()

    summary = asyncio.run(svc.reconcile_on_startup(mock_db))

    assert summary["stuck_submissions_marked_failed"] == 2
    assert queued.status == CodeSubmissionStatus.FAILED
    assert queued.error_message == "interrupted by a backend restart, needs manual re-grade"
    assert grading.status == CodeSubmissionStatus.FAILED
    mock_db.commit.assert_called()


def test_reconcile_submission_query_filters_to_queued_and_grading_only():
    """Terminal-state rows (graded/failed/partial_failed) must never be selected in
    the first place — the loop body has no guard of its own, so correctness here
    depends entirely on the query's WHERE clause matching exactly these two statuses."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _mock_execute_result([]), _mock_execute_result([]), _mock_execute_result([]),
    ])
    mock_db.commit = AsyncMock()

    asyncio.run(svc.reconcile_on_startup(mock_db))

    submission_query = mock_db.execute.call_args_list[2][0][0]
    compiled = str(submission_query.compile(compile_kwargs={"literal_binds": True}))
    assert "'queued'" in compiled
    assert "'grading'" in compiled
    assert "'graded'" not in compiled
    assert "'partial_failed'" not in compiled
    assert "'failed'" not in compiled


def test_reconcile_noop_when_nothing_stuck():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _mock_execute_result([]), _mock_execute_result([]), _mock_execute_result([]),
    ])
    mock_db.commit = AsyncMock()

    summary = asyncio.run(svc.reconcile_on_startup(mock_db))

    assert summary == {
        "lifetime_cap_jobs_rescheduled": 0,
        "stuck_provisions_marked_failed": 0,
        "stuck_submissions_marked_failed": 0,
    }
    mock_db.commit.assert_not_called()
