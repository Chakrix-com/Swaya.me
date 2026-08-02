"""
Unit tests for GET /quiz-builder/questions/{id}/coding-challenge-review (6.8).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from broker.api import coding_challenge as router_mod
from persistence.models.quiz import (
    Quiz, Question, CodeWorkspace, CodeWorkspaceStatus, CodeSubmission, CodeSubmissionStatus,
    CodingChallengeInvite,
)


def _mock_db(question, quiz, workspaces, submissions_by_workspace_id, invites=None):
    db = AsyncMock()
    invites_result = MagicMock()
    invites_result.scalars.return_value.all.return_value = invites or []
    ws_result = MagicMock()
    ws_result.scalars.return_value.all.return_value = workspaces

    call_count = {"n": 0}

    async def execute_side_effect(query):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return invites_result
        if call_count["n"] == 2:
            return ws_result
        # The endpoint iterates candidates via a Python set (all_emails), so
        # per-workspace submission queries don't fire in `workspaces` list order —
        # resolve the right submission from the query's own bound workspace_id
        # instead of relying on call sequence.
        params = query.compile().params
        workspace_id = next(v for k, v in params.items() if k.startswith("workspace_id"))
        r = MagicMock()
        r.scalar_one_or_none.return_value = submissions_by_workspace_id.get(workspace_id)
        return r

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.get = AsyncMock(side_effect=[question, quiz])
    return db


def test_review_404_when_question_missing():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    current_user = MagicMock(tenant_id=1)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod.get_coding_challenge_review(999, db, current_user))
    assert exc_info.value.status_code == 404


def test_review_rejects_cross_tenant_access():
    question = Question(id=10, quiz_id=1, question_type="coding_challenge", text="x", order=0)
    quiz = Quiz(id=1, tenant_id=5, event_id=1, title="Q")
    db = AsyncMock()
    db.get = AsyncMock(side_effect=[question, quiz])
    current_user = MagicMock(tenant_id=999)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod.get_coding_challenge_review(10, db, current_user))
    assert exc_info.value.status_code == 403


def test_review_returns_one_entry_per_candidate():
    """A question can have many candidates (repeated /invite calls) — must list
    all of them, not assume a single submission."""
    question = Question(id=10, quiz_id=1, question_type="coding_challenge", text="x", order=0)
    quiz = Quiz(id=1, tenant_id=5, event_id=1, title="Q")
    ws1 = CodeWorkspace(id=1, tenant_id=5, quiz_id=1, question_id=10, candidate_email="alice@x.com",
                         ide_type="code_server", coder_workspace_name="ws-1",
                         status=CodeWorkspaceStatus.SUBMITTED)
    ws2 = CodeWorkspace(id=2, tenant_id=5, quiz_id=1, question_id=10, candidate_email="bob@x.com",
                         ide_type="code_server", coder_workspace_name="ws-2",
                         status=CodeWorkspaceStatus.ACTIVE)
    sub1 = CodeSubmission(
        id=1, workspace_id=1, question_id=10, status=CodeSubmissionStatus.GRADED,
        ai_score=90, ai_verdict="pass", test_output="all good", passed_count=5, total_count=5,
    )
    db = _mock_db(question, quiz, [ws1, ws2], {1: sub1})  # bob never submitted
    current_user = MagicMock(tenant_id=5)

    result = asyncio.run(router_mod.get_coding_challenge_review(10, db, current_user))

    assert result["question_id"] == 10
    assert len(result["candidates"]) == 2
    alice = next(c for c in result["candidates"] if c["candidate_email"] == "alice@x.com")
    bob = next(c for c in result["candidates"] if c["candidate_email"] == "bob@x.com")
    assert alice["submission"]["status"] == "graded"
    assert alice["submission"]["ai_score"] == 90
    assert bob["submission"] is None
    assert bob["workspace_status"] == "active"


def test_review_includes_partial_failed_state_with_error_message():
    question = Question(id=10, quiz_id=1, question_type="coding_challenge", text="x", order=0)
    quiz = Quiz(id=1, tenant_id=5, event_id=1, title="Q")
    ws1 = CodeWorkspace(id=1, tenant_id=5, quiz_id=1, question_id=10, candidate_email="alice@x.com",
                         ide_type="code_server", coder_workspace_name="ws-1",
                         status=CodeWorkspaceStatus.SUBMITTED)
    sub1 = CodeSubmission(
        id=1, workspace_id=1, question_id=10, status=CodeSubmissionStatus.PARTIAL_FAILED,
        error_message="Gemini unreachable", test_output="output", passed_count=3, total_count=5,
        code_timeline="commit log", ai_transcript_raw="transcript",
    )
    db = _mock_db(question, quiz, [ws1], {1: sub1})
    current_user = MagicMock(tenant_id=5)

    result = asyncio.run(router_mod.get_coding_challenge_review(10, db, current_user))

    entry = result["candidates"][0]["submission"]
    assert entry["status"] == "partial_failed"
    assert entry["error_message"] == "Gemini unreachable"
    assert entry["score_breakdown"] is None
    # everything harvested is still visible to the examiner
    assert entry["code_timeline"] == "commit log"
    assert entry["ai_transcript_raw"] == "transcript"


def test_review_empty_when_no_candidates_yet():
    question = Question(id=10, quiz_id=1, question_type="coding_challenge", text="x", order=0)
    quiz = Quiz(id=1, tenant_id=5, event_id=1, title="Q")
    db = _mock_db(question, quiz, [], {})
    current_user = MagicMock(tenant_id=5)
    result = asyncio.run(router_mod.get_coding_challenge_review(10, db, current_user))
    assert result == {"question_id": 10, "quiz_id": 1, "has_custom_weights": False, "candidates": []}
