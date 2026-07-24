"""
Unit tests for POST /coding-challenge/{token}/start (6.4): OTP guard, concurrency
guard, idempotency guard, lifetime-cap job scheduling. Route handler called
directly with mocked db/redis, matching this repo's test convention.
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from broker.api import coding_challenge as router_mod
from persistence.models.quiz import (
    Quiz, Question, CodeWorkspace, CodeWorkspaceStatus,
)


def _make_token(quiz_id=1, question_id=10, email="candidate@example.com") -> str:
    return router_mod.svc.create_invite_token(quiz_id, question_id, email)


def _mock_db(existing_workspace=None, active_count=0, question=None, quiz=None):
    db = AsyncMock()
    idempotency_result = MagicMock()
    idempotency_result.scalar_one_or_none.return_value = existing_workspace
    count_result = MagicMock()
    count_result.scalar_one.return_value = active_count
    db.execute = AsyncMock(side_effect=[idempotency_result, count_result])
    db.get = AsyncMock(side_effect=[question, quiz])
    db.commit = AsyncMock()

    async def fake_refresh(obj):
        # Mirrors what a real flush/refresh populates (created_at's Python-side
        # default), since this bare mock never actually goes through SQLAlchemy.
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.utcnow()
        if getattr(obj, "id", None) is None:
            obj.id = 1
    db.refresh = AsyncMock(side_effect=fake_refresh)
    db.add = MagicMock()
    return db


# ── OTP guard ────────────────────────────────────────────────────────────────

def test_start_rejects_invalid_otp_before_anything_else():
    token = _make_token()
    body = router_mod.StartRequest(ide_type="code_server", otp="000000")
    db = AsyncMock()
    redis = AsyncMock()

    with patch.object(router_mod.svc, "verify_coding_challenge_otp", AsyncMock(return_value=False)), \
         patch.object(router_mod.coder_client, "create_workspace", AsyncMock()) as mock_create:
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(router_mod.start_coding_challenge(token, body, db, redis))

    assert exc_info.value.status_code == 400
    mock_create.assert_not_called()  # no workspace ever created for an unverified candidate
    db.execute.assert_not_called()  # never even reaches the idempotency/concurrency checks


def test_start_rejects_invalid_ide_type_before_otp_check():
    token = _make_token()
    body = router_mod.StartRequest(ide_type="vim", otp="123456")
    db = AsyncMock()
    redis = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod.start_coding_challenge(token, body, db, redis))
    assert exc_info.value.status_code == 400


# ── Concurrency guard ────────────────────────────────────────────────────────

def test_start_rejects_when_at_capacity():
    token = _make_token()
    body = router_mod.StartRequest(ide_type="code_server", otp="123456")
    db = _mock_db(existing_workspace=None, active_count=5)  # default MAX_CONCURRENT_WORKSPACES=5
    redis = AsyncMock()

    with patch.object(router_mod.svc, "verify_coding_challenge_otp", AsyncMock(return_value=True)), \
         patch.object(router_mod.coder_client, "create_workspace", AsyncMock()) as mock_create:
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(router_mod.start_coding_challenge(token, body, db, redis))

    assert exc_info.value.status_code == 429
    mock_create.assert_not_called()


def test_start_allows_when_under_capacity():
    token = _make_token()
    body = router_mod.StartRequest(ide_type="code_server", otp="123456")
    question = Question(id=10, quiz_id=1, git_repo_url="https://github.com/x/y")
    quiz = Quiz(id=1, tenant_id=1, event_id=1, title="Q")
    db = _mock_db(existing_workspace=None, active_count=4, question=question, quiz=quiz)
    redis = AsyncMock()

    with patch.object(router_mod.svc, "verify_coding_challenge_otp", AsyncMock(return_value=True)), \
         patch.object(router_mod.coder_client, "create_workspace", AsyncMock()) as mock_create, \
         patch.object(router_mod.coder_client, "mint_session_url",
                       AsyncMock(return_value=("https://sandbox/url", "tok-name"))), \
         patch.object(router_mod.svc, "schedule_lifetime_cap_job") as mock_schedule:
        result = asyncio.run(router_mod.start_coding_challenge(token, body, db, redis))

    mock_create.assert_called_once()
    assert result == {"workspace_url": "https://sandbox/url"}
    mock_schedule.assert_called_once()


# ── Idempotency guard ────────────────────────────────────────────────────────

def test_start_reconnects_to_existing_active_workspace_without_reprovisioning():
    token = _make_token()
    body = router_mod.StartRequest(ide_type="code_server", otp="123456")
    existing = CodeWorkspace(
        id=1, tenant_id=1, quiz_id=1, question_id=10, candidate_email="candidate@example.com",
        ide_type="code_server", coder_workspace_name="cc-1-10-abcd1234",
        status=CodeWorkspaceStatus.ACTIVE,
    )
    db = _mock_db(existing_workspace=existing)
    redis = AsyncMock()

    with patch.object(router_mod.svc, "verify_coding_challenge_otp", AsyncMock(return_value=True)), \
         patch.object(router_mod.coder_client, "create_workspace", AsyncMock()) as mock_create, \
         patch.object(router_mod.coder_client, "mint_session_url",
                       AsyncMock(return_value=("https://sandbox/reconnect-url", "tok-name-2"))) as mock_mint:
        result = asyncio.run(router_mod.start_coding_challenge(token, body, db, redis))

    mock_create.assert_not_called()  # never re-provisions
    mock_mint.assert_called_once_with(
        "cc-1-10-abcd1234", "code_server", router_mod.settings.coder.url,
        router_mod.settings.coder.service_account_username,
    )
    assert result == {"workspace_url": "https://sandbox/reconnect-url"}
    db.commit.assert_called_once()


def test_start_ignores_stale_destroyed_workspace_and_reprovisions():
    """An idempotency-check hit on a long-abandoned/destroyed row must not block a
    genuinely fresh provision."""
    token = _make_token()
    body = router_mod.StartRequest(ide_type="code_server", otp="123456")
    stale = CodeWorkspace(
        id=1, tenant_id=1, quiz_id=1, question_id=10, candidate_email="candidate@example.com",
        ide_type="code_server", coder_workspace_name="cc-1-10-abcd1234",
        status=CodeWorkspaceStatus.DESTROYED,
    )
    question = Question(id=10, quiz_id=1, git_repo_url="https://github.com/x/y")
    quiz = Quiz(id=1, tenant_id=1, event_id=1, title="Q")
    db = _mock_db(existing_workspace=stale, active_count=0, question=question, quiz=quiz)
    redis = AsyncMock()

    with patch.object(router_mod.svc, "verify_coding_challenge_otp", AsyncMock(return_value=True)), \
         patch.object(router_mod.coder_client, "create_workspace", AsyncMock()) as mock_create, \
         patch.object(router_mod.coder_client, "mint_session_url",
                       AsyncMock(return_value=("https://sandbox/new-url", "tok-new"))), \
         patch.object(router_mod.svc, "schedule_lifetime_cap_job"):
        asyncio.run(router_mod.start_coding_challenge(token, body, db, redis))

    mock_create.assert_called_once()  # DOES re-provision since the old one is gone


# ── Lifetime-cap job scheduling ─────────────────────────────────────────────

def test_start_schedules_lifetime_cap_job_with_correct_deadline():
    token = _make_token()
    body = router_mod.StartRequest(ide_type="intellij", otp="123456")
    question = Question(id=10, quiz_id=1, git_repo_url="https://github.com/x/y")
    quiz = Quiz(id=1, tenant_id=1, event_id=1, title="Q")
    db = _mock_db(existing_workspace=None, active_count=0, question=question, quiz=quiz)
    redis = AsyncMock()

    async def fake_refresh(workspace):
        workspace.id = 42
        workspace.created_at = datetime(2026, 1, 1, 0, 0, 0)
    db.refresh = AsyncMock(side_effect=fake_refresh)

    with patch.object(router_mod.svc, "verify_coding_challenge_otp", AsyncMock(return_value=True)), \
         patch.object(router_mod.coder_client, "create_workspace", AsyncMock()), \
         patch.object(router_mod.coder_client, "mint_session_url",
                       AsyncMock(return_value=("https://sandbox/url", "tok"))), \
         patch.object(router_mod.svc, "schedule_lifetime_cap_job") as mock_schedule:
        asyncio.run(router_mod.start_coding_challenge(token, body, db, redis))

    workspace_id, workspace_name, fire_at = mock_schedule.call_args[0]
    assert workspace_id == 42
    assert workspace_name == "cc-1-10-" + router_mod._derive_workspace_name(1, 10, "candidate@example.com").split("-")[-1]
    expected_deadline = datetime(2026, 1, 1, 0, 0, 0) + router_mod.timedelta(
        seconds=router_mod.settings.coder.workspace_max_lifetime_seconds
    )
    assert fire_at == expected_deadline


def test_derive_workspace_name_deterministic_and_scoped():
    name1 = router_mod._derive_workspace_name(1, 10, "a@b.com")
    name2 = router_mod._derive_workspace_name(1, 10, "a@b.com")
    name3 = router_mod._derive_workspace_name(1, 10, "different@b.com")
    assert name1 == name2
    assert name1 != name3
    assert name1.startswith("cc-1-10-")
