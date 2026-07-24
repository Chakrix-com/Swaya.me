"""
Unit tests for the invite/info endpoints in broker.api.coding_challenge (6.1/6.2/6.9).
Calls route handler functions directly with mocked db/current_user, matching this
repo's existing test convention (no FastAPI TestClient precedent to follow).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from broker.api import coding_challenge as router_mod
from persistence.models.quiz import Quiz, QuizType, Question, QuestionType


def _fixture_quiz(quiz_type=QuizType.CODING_CHALLENGE, tenant_id=1) -> Quiz:
    return Quiz(id=1, tenant_id=tenant_id, event_id=1, title="My Challenge", quiz_type=quiz_type)


def _fixture_question(quiz_id=1, question_type=QuestionType.CODING_CHALLENGE) -> Question:
    return Question(
        id=10, quiz_id=quiz_id, question_type=question_type, text="Solve it", order=0,
        git_repo_url="https://github.com/octocat/Hello-World",
    )


def _mock_db_with_scalar_results(*results):
    """Each call to db.execute returns the next result in sequence."""
    db = AsyncMock()
    mocks = []
    for r in results:
        m = MagicMock()
        m.scalar_one_or_none.return_value = r
        m.scalars.return_value.first.return_value = r
        mocks.append(m)
    db.execute = AsyncMock(side_effect=mocks)
    return db


# ── _get_coding_challenge_question ──────────────────────────────────────────

def test_get_coding_challenge_question_found():
    quiz = _fixture_quiz()
    question = _fixture_question()
    db = _mock_db_with_scalar_results(quiz, question)
    result_quiz, result_question = asyncio.run(router_mod._get_coding_challenge_question(db, 1))
    assert result_quiz is quiz
    assert result_question is question


def test_get_coding_challenge_question_wrong_quiz_type_404():
    quiz = _fixture_quiz(quiz_type=QuizType.QUIZ)
    db = _mock_db_with_scalar_results(quiz)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod._get_coding_challenge_question(db, 1))
    assert exc_info.value.status_code == 404


def test_get_coding_challenge_question_no_quiz_404():
    db = _mock_db_with_scalar_results(None)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod._get_coding_challenge_question(db, 999))
    assert exc_info.value.status_code == 404


def test_get_coding_challenge_question_missing_question_400():
    quiz = _fixture_quiz()
    db = _mock_db_with_scalar_results(quiz, None)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod._get_coding_challenge_question(db, 1))
    assert exc_info.value.status_code == 400


# ── invite_candidate ─────────────────────────────────────────────────────────

def test_invite_candidate_mints_token_and_sends_email():
    quiz = _fixture_quiz(tenant_id=5)
    question = _fixture_question()
    db = _mock_db_with_scalar_results(quiz, question)
    current_user = MagicMock(tenant_id=5)
    body = router_mod.InviteRequest(candidate_email="candidate@example.com")

    with patch("core.auth.email_service.send_email", AsyncMock(return_value=True)) as mock_send:
        result = asyncio.run(router_mod.invite_candidate(1, body, db, current_user))

    assert result["sent"] is True
    assert "/c/" in result["invite_url"]
    mock_send.assert_called_once()
    recipients = mock_send.call_args.kwargs.get("recipients") or mock_send.call_args[1].get("recipients")
    assert recipients == ["candidate@example.com"]


def test_invite_candidate_rejects_cross_tenant_access():
    quiz = _fixture_quiz(tenant_id=5)
    question = _fixture_question()
    db = _mock_db_with_scalar_results(quiz, question)
    current_user = MagicMock(tenant_id=999)  # different tenant
    body = router_mod.InviteRequest(candidate_email="candidate@example.com")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod.invite_candidate(1, body, db, current_user))
    assert exc_info.value.status_code == 403


# ── get_coding_challenge_info ────────────────────────────────────────────────

def test_get_coding_challenge_info_returns_expected_shape():
    question = _fixture_question()
    quiz = _fixture_quiz()
    token = router_mod.svc.create_invite_token(1, 10, "candidate@example.com")

    db = AsyncMock()
    db.get = AsyncMock(side_effect=[question, quiz])

    with patch.object(router_mod.svc, "fetch_readme", AsyncMock(return_value="# Problem\nDo the thing")):
        result = asyncio.run(router_mod.get_coding_challenge_info(token, db))

    assert result["quiz_title"] == "My Challenge"
    assert result["problem_statement"] == "# Problem\nDo the thing"
    assert result["candidate_email"] == "candidate@example.com"
    assert set(result["ide_choices"]) == {"code_server", "intellij"}


def test_get_coding_challenge_info_404_when_question_missing():
    token = router_mod.svc.create_invite_token(1, 10, "candidate@example.com")
    db = AsyncMock()
    db.get = AsyncMock(side_effect=[None, _fixture_quiz()])
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod.get_coding_challenge_info(token, db))
    assert exc_info.value.status_code == 404


def test_get_coding_challenge_info_rejects_invalid_token():
    db = AsyncMock()
    with pytest.raises(HTTPException):
        asyncio.run(router_mod.get_coding_challenge_info("not-a-real-token", db))
