"""
Unit tests for POST /coding-challenge/{token}/submit (6.5): idempotency guard,
and confirms /submit returns fast without blocking on the grading job itself.
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from broker.api import coding_challenge as router_mod
from persistence.models.quiz import (
    CodeWorkspace, CodeWorkspaceStatus, CodeSubmission, CodeSubmissionStatus,
)


def _make_token(quiz_id=1, question_id=10, email="candidate@example.com") -> str:
    return router_mod.svc.create_invite_token(quiz_id, question_id, email)


def _mock_db(workspace, existing_submission=None):
    db = AsyncMock()
    ws_result = MagicMock()
    ws_result.scalar_one_or_none.return_value = workspace
    sub_result = MagicMock()
    sub_result.scalar_one_or_none.return_value = existing_submission
    db.execute = AsyncMock(side_effect=[ws_result, sub_result])
    db.commit = AsyncMock()

    async def fake_refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = 99
    db.refresh = AsyncMock(side_effect=fake_refresh)
    db.add = MagicMock()
    return db


def _fixture_workspace(status=CodeWorkspaceStatus.ACTIVE) -> CodeWorkspace:
    return CodeWorkspace(
        id=1, tenant_id=1, quiz_id=1, question_id=10, candidate_email="candidate@example.com",
        ide_type="code_server", coder_workspace_name="cc-1-10-abcd1234",
        coder_token_name="cc-1-10-abcd1234-session", status=status,
    )


def test_submit_404_when_no_workspace_exists():
    token = _make_token()
    db = _mock_db(workspace=None)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod.submit_coding_challenge(token, db))
    assert exc_info.value.status_code == 404


def test_submit_first_call_revokes_and_schedules_grading():
    token = _make_token()
    workspace = _fixture_workspace()
    db = _mock_db(workspace=workspace, existing_submission=None)
    mock_scheduler = MagicMock()

    with patch.object(router_mod.coder_client, "revoke_token", AsyncMock()) as mock_revoke, \
         patch("core.stats.scheduler.scheduler", mock_scheduler):
        result = asyncio.run(router_mod.submit_coding_challenge(token, db))

    assert result == {"status": "queued"}
    mock_revoke.assert_called_once_with("cc-1-10-abcd1234-session")
    assert workspace.status == CodeWorkspaceStatus.SUBMITTED
    assert workspace.submitted_at is not None
    mock_scheduler.add_job.assert_called_once()
    _, kwargs = mock_scheduler.add_job.call_args
    assert kwargs["args"] == [99]


def test_submit_is_idempotent_does_not_double_revoke_or_reschedule():
    """A second /submit for an already-submitted workspace must not re-revoke the
    token or schedule a second grading job — just return the existing status."""
    token = _make_token()
    workspace = _fixture_workspace(status=CodeWorkspaceStatus.SUBMITTED)
    existing_submission = CodeSubmission(
        id=5, workspace_id=1, question_id=10, status=CodeSubmissionStatus.GRADING,
    )
    db = _mock_db(workspace=workspace, existing_submission=existing_submission)
    mock_scheduler = MagicMock()

    with patch.object(router_mod.coder_client, "revoke_token", AsyncMock()) as mock_revoke, \
         patch("core.stats.scheduler.scheduler", mock_scheduler):
        result = asyncio.run(router_mod.submit_coding_challenge(token, db))

    assert result == {"status": "grading"}
    mock_revoke.assert_not_called()
    mock_scheduler.add_job.assert_not_called()
    db.commit.assert_not_called()


def test_submit_returns_immediately_without_awaiting_grading_job():
    """/submit must not block on the grading job itself — it only schedules it.
    Confirms run_grading_job is never awaited directly from within submit."""
    token = _make_token()
    workspace = _fixture_workspace()
    db = _mock_db(workspace=workspace, existing_submission=None)
    mock_scheduler = MagicMock()

    with patch.object(router_mod.coder_client, "revoke_token", AsyncMock()), \
         patch("core.stats.scheduler.scheduler", mock_scheduler), \
         patch("features.coding_challenge.grading_service_async.run_grading_job",
               AsyncMock(side_effect=AssertionError("must not be awaited directly by submit"))):
        result = asyncio.run(router_mod.submit_coding_challenge(token, db))

    assert result == {"status": "queued"}  # returned fine — the patched fn was never called


def test_submit_tolerates_revoke_token_failure():
    """A revoke_token failure (e.g. token already expired) must not block the
    submission from being recorded as queued."""
    token = _make_token()
    workspace = _fixture_workspace()
    db = _mock_db(workspace=workspace, existing_submission=None)
    mock_scheduler = MagicMock()

    with patch.object(router_mod.coder_client, "revoke_token",
                       AsyncMock(side_effect=Exception("token already gone"))), \
         patch("core.stats.scheduler.scheduler", mock_scheduler):
        result = asyncio.run(router_mod.submit_coding_challenge(token, db))

    assert result == {"status": "queued"}
    assert workspace.status == CodeWorkspaceStatus.SUBMITTED


def test_submit_skips_revoke_when_no_token_name_persisted():
    token = _make_token()
    workspace = _fixture_workspace()
    workspace.coder_token_name = None
    db = _mock_db(workspace=workspace, existing_submission=None)
    mock_scheduler = MagicMock()

    with patch.object(router_mod.coder_client, "revoke_token", AsyncMock()) as mock_revoke, \
         patch("core.stats.scheduler.scheduler", mock_scheduler):
        asyncio.run(router_mod.submit_coding_challenge(token, db))

    mock_revoke.assert_not_called()
