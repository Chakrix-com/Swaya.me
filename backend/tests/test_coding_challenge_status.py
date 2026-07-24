"""
Unit tests for GET /coding-challenge/{token}/status (6.7).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from broker.api import coding_challenge as router_mod
from persistence.models.quiz import CodeWorkspace, CodeSubmission, CodeSubmissionStatus


def _make_token() -> str:
    return router_mod.svc.create_invite_token(1, 10, "candidate@example.com")


def _mock_db(workspace, submission):
    db = AsyncMock()
    ws_result = MagicMock()
    ws_result.scalar_one_or_none.return_value = workspace
    sub_result = MagicMock()
    sub_result.scalar_one_or_none.return_value = submission
    db.execute = AsyncMock(side_effect=[ws_result, sub_result])
    return db


def test_status_404_when_no_workspace():
    db = _mock_db(workspace=None, submission=None)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod.get_coding_challenge_status(_make_token(), db))
    assert exc_info.value.status_code == 404


def test_status_not_submitted_when_no_submission_yet():
    workspace = CodeWorkspace(id=1, tenant_id=1, quiz_id=1, question_id=10,
                               candidate_email="candidate@example.com", ide_type="code_server",
                               coder_workspace_name="ws-1")
    db = _mock_db(workspace=workspace, submission=None)
    result = asyncio.run(router_mod.get_coding_challenge_status(_make_token(), db))
    assert result == {"status": "not_submitted"}


def test_status_queued():
    workspace = CodeWorkspace(id=1, tenant_id=1, quiz_id=1, question_id=10,
                               candidate_email="candidate@example.com", ide_type="code_server",
                               coder_workspace_name="ws-1")
    submission = CodeSubmission(id=1, workspace_id=1, question_id=10, status=CodeSubmissionStatus.QUEUED)
    db = _mock_db(workspace=workspace, submission=submission)
    result = asyncio.run(router_mod.get_coding_challenge_status(_make_token(), db))
    assert result == {"status": "queued"}


def test_status_graded_includes_score_and_verdict():
    workspace = CodeWorkspace(id=1, tenant_id=1, quiz_id=1, question_id=10,
                               candidate_email="candidate@example.com", ide_type="code_server",
                               coder_workspace_name="ws-1")
    submission = CodeSubmission(
        id=1, workspace_id=1, question_id=10, status=CodeSubmissionStatus.GRADED,
        ai_score=82, ai_verdict="pass",
    )
    db = _mock_db(workspace=workspace, submission=submission)
    result = asyncio.run(router_mod.get_coding_challenge_status(_make_token(), db))
    assert result == {"status": "graded", "ai_score": 82, "ai_verdict": "pass"}


def test_status_partial_failed_includes_error_message_not_score():
    workspace = CodeWorkspace(id=1, tenant_id=1, quiz_id=1, question_id=10,
                               candidate_email="candidate@example.com", ide_type="code_server",
                               coder_workspace_name="ws-1")
    submission = CodeSubmission(
        id=1, workspace_id=1, question_id=10, status=CodeSubmissionStatus.PARTIAL_FAILED,
        error_message="Gemini unreachable",
    )
    db = _mock_db(workspace=workspace, submission=submission)
    result = asyncio.run(router_mod.get_coding_challenge_status(_make_token(), db))
    assert result == {"status": "partial_failed", "error_message": "Gemini unreachable"}
    assert "ai_score" not in result


def test_status_failed_includes_error_message():
    workspace = CodeWorkspace(id=1, tenant_id=1, quiz_id=1, question_id=10,
                               candidate_email="candidate@example.com", ide_type="code_server",
                               coder_workspace_name="ws-1")
    submission = CodeSubmission(
        id=1, workspace_id=1, question_id=10, status=CodeSubmissionStatus.FAILED,
        error_message="interrupted by a backend restart, needs manual re-grade",
    )
    db = _mock_db(workspace=workspace, submission=submission)
    result = asyncio.run(router_mod.get_coding_challenge_status(_make_token(), db))
    assert result["status"] == "failed"
    assert "interrupted" in result["error_message"]
