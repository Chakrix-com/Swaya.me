"""
Grading-mode-selector feature (2026-08-09): Question.grading_mode is a new
per-question setting (AI_JUDGED / HYBRID / DETERMINISTIC) mirroring the
existing grading_weights override. Covers the same class of bug that
test_quiz_service_coding_challenge_fields.py caught for the coding-challenge
fields: a schema field that exists but silently doesn't reach every place a
Question gets constructed, copied, or serialized. See
_private/coding_challenge_grading_mode_plan_20260809.md §1 and the 5th/8th
review-pass findings for why each of these copy points matters.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.quiz.schemas import QuestionCreate, QuestionUpdate, QuestionResponse, GradingModeEnum
from features.quiz.question_service_async import QuestionServiceAsync
from features.quiz.quiz_service_async import QuizBuilderServiceAsync
from persistence.models.quiz import (
    Quiz, QuizType, QuizStatus, TemplateScope, Question, QuestionType, GradingMode,
)


# ─── Schema validation (pure, no DB) ──────────────────────────────────────

def test_question_create_defaults_to_hybrid():
    q = QuestionCreate(text="hi", question_type="coding_challenge")
    assert q.grading_mode == GradingModeEnum.HYBRID


def test_question_update_accepts_valid_mode():
    q = QuestionUpdate(grading_mode="deterministic")
    assert q.grading_mode == GradingModeEnum.DETERMINISTIC


def test_question_update_rejects_invalid_mode():
    with pytest.raises(Exception):
        QuestionUpdate(grading_mode="not_a_real_mode")


def test_question_response_accepts_all_three_modes():
    for mode in ("ai_judged", "hybrid", "deterministic"):
        r = QuestionResponse(id=1, question_type="coding_challenge", text="hi", order=1, grading_mode=mode)
        assert r.grading_mode == GradingModeEnum(mode)


# ─── question_service_async: _to_question_response passthrough ───────────

def _fixture_coding_challenge_question(grading_mode=GradingMode.DETERMINISTIC, **overrides):
    defaults = dict(
        id=8, quiz_id=15, question_type=QuestionType.CODING_CHALLENGE, text="Solve it", order=0,
        points=1, grading_weights={"functional_correctness": 100}, grading_mode=grading_mode,
    )
    defaults.update(overrides)
    return Question(**defaults)


def test_to_question_response_includes_grading_mode():
    service = QuestionServiceAsync(tier_service=MagicMock())
    question = _fixture_coding_challenge_question()

    response = service._to_question_response(question)

    assert response.grading_mode == GradingModeEnum.DETERMINISTIC


# ─── question_service_async: create / update wiring ───────────────────────

def _mock_user(**overrides):
    defaults = dict(tenant_id=1, user_id=1)
    defaults.update(overrides)
    user = MagicMock()
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


@pytest.mark.asyncio
async def test_add_question_persists_grading_mode():
    service = QuestionServiceAsync(tier_service=AsyncMock())
    service.tier_service.check_question_limit = AsyncMock(return_value=True)
    quiz = Quiz(
        id=15, event_id=15, tenant_id=1, title="Q", quiz_type=QuizType.CODING_CHALLENGE,
        status=QuizStatus.DRAFT, is_template=False, template_scope=TemplateScope.TENANT,
    )
    quiz.__dict__["questions"] = []
    request = QuestionCreate(
        text="hi", question_type="coding_challenge", grading_mode="ai_judged", from_ai=True,
    )

    db = AsyncMock()
    quiz_result = MagicMock()
    quiz_result.scalar_one_or_none = MagicMock(return_value=quiz)
    db.execute = AsyncMock(return_value=quiz_result)
    added = []
    db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    db.commit = AsyncMock()

    def _assign_id(obj):
        obj.id = 42
    db.refresh = AsyncMock(side_effect=_assign_id)

    await service.add_question(db, quiz_id=15, request=request, current_user=_mock_user())

    assert len(added) == 1
    assert added[0].grading_mode == GradingModeEnum.AI_JUDGED


@pytest.mark.asyncio
async def test_update_question_only_sets_grading_mode_when_field_present():
    service = QuestionServiceAsync(tier_service=MagicMock())
    question = _fixture_coding_challenge_question(grading_mode=GradingMode.HYBRID)
    question.quiz = Quiz(id=15, status=QuizStatus.DRAFT)
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=question)
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()

    # Field not set at all — must not touch the existing value.
    await service.update_question(
        db, question_id=8, request=QuestionUpdate(), current_user=_mock_user(),
    )
    assert question.grading_mode == GradingMode.HYBRID

    # Field explicitly set — must update.
    await service.update_question(
        db, question_id=8,
        request=QuestionUpdate(grading_mode="deterministic"), current_user=_mock_user(),
    )
    assert question.grading_mode == GradingModeEnum.DETERMINISTIC


# ─── question_service_async: duplicate_question copies grading_mode ──────

@pytest.mark.asyncio
async def test_duplicate_question_copies_grading_mode():
    service = QuestionServiceAsync(tier_service=MagicMock())
    quiz = Quiz(
        id=15, event_id=15, tenant_id=1, title="Q", quiz_type=QuizType.CODING_CHALLENGE,
        status=QuizStatus.DRAFT, is_template=False, template_scope=TemplateScope.TENANT,
    )
    source = _fixture_coding_challenge_question(grading_mode=GradingMode.DETERMINISTIC, order=0)
    source.quiz = quiz

    db = AsyncMock()
    select_result = MagicMock()
    select_result.scalar_one_or_none = MagicMock(return_value=source)
    after_result = MagicMock()
    after_result.scalars.return_value.all = MagicMock(return_value=[])
    db.execute = AsyncMock(side_effect=[select_result, MagicMock(), after_result])

    added = []
    db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    db.commit = AsyncMock()

    def _assign_id(obj):
        obj.id = 43
    db.refresh = AsyncMock(side_effect=_assign_id)

    with patch.object(service, "_editable_quiz_condition", return_value=True):
        await service.duplicate_question(db, quiz_id=15, question_id=8, current_user=_mock_user())

    assert len(added) == 1
    assert added[0].grading_mode == GradingMode.DETERMINISTIC


# ─── quiz_service_async: _to_quiz_response includes grading_mode ─────────

def test_to_quiz_response_includes_grading_mode():
    service = QuizBuilderServiceAsync(tier_service=MagicMock())
    question = Question(
        id=8, quiz_id=15, question_type=QuestionType.CODING_CHALLENGE, text="Solve it", order=0,
        points=1, grading_mode=GradingMode.AI_JUDGED,
    )
    quiz = Quiz(
        id=15, event_id=15, tenant_id=1, title="Q", quiz_type=QuizType.CODING_CHALLENGE,
        status=QuizStatus.READY, is_template=False, template_scope=TemplateScope.TENANT,
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )
    quiz.__dict__["questions"] = [question]
    quiz.__dict__["folder"] = None

    response = service._to_quiz_response(quiz)

    assert response.questions[0].grading_mode == GradingModeEnum.AI_JUDGED


# ─── quiz_service_async: duplicate_quiz copies coding-challenge fields ────
# Regression test for the pre-existing bug found while wiring grading_mode
# through (5th review pass): duplicate_quiz had its own, much narrower
# Question(...) copy list that dropped grading_weights and every other
# coding-challenge field, independent of grading_mode. Fixed alongside.

@pytest.mark.asyncio
async def test_duplicate_quiz_copies_coding_challenge_fields():
    service = QuizBuilderServiceAsync(tier_service=MagicMock())
    source_question = Question(
        id=8, quiz_id=15, question_type=QuestionType.CODING_CHALLENGE, text="Solve it", order=0,
        points=1, git_repo_url="https://github.com/x/y", test_command="mvn test",
        hidden_test_content="hidden", hidden_test_filename="Hidden.java",
        time_budget_seconds=1800, grading_weights={"functional_correctness": 100},
        grading_rubric="be thorough", grading_mode=GradingMode.DETERMINISTIC,
    )
    source_quiz = Quiz(
        id=15, event_id=15, tenant_id=1, title="Q", quiz_type=QuizType.CODING_CHALLENGE,
        status=QuizStatus.READY, is_template=False, template_scope=TemplateScope.TENANT,
    )
    source_quiz.__dict__["questions"] = [source_question]

    duplicated_quiz = Quiz(
        id=99, event_id=15, tenant_id=1, title="Q (Copy)", quiz_type=QuizType.CODING_CHALLENGE,
        status=QuizStatus.DRAFT, is_template=False, template_scope=TemplateScope.TENANT,
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )
    duplicated_quiz.__dict__["questions"] = []
    duplicated_quiz.__dict__["folder"] = None

    db = AsyncMock()
    added = []
    db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    reload_result = MagicMock()
    reload_result.scalar_one = MagicMock(return_value=duplicated_quiz)
    db.execute = AsyncMock(return_value=reload_result)

    with patch.object(service, "_get_editable_quiz", AsyncMock(return_value=source_quiz)):
        await service.duplicate_quiz(db, quiz_id=15, current_user=MagicMock(tenant_id=1))

    copied_questions = [obj for obj in added if isinstance(obj, Question)]
    assert len(copied_questions) == 1
    copy = copied_questions[0]
    assert copy.git_repo_url == "https://github.com/x/y"
    assert copy.test_command == "mvn test"
    assert copy.hidden_test_content == "hidden"
    assert copy.hidden_test_filename == "Hidden.java"
    assert copy.time_budget_seconds == 1800
    assert copy.grading_weights == {"functional_correctness": 100}
    assert copy.grading_rubric == "be thorough"
    assert copy.grading_mode == GradingMode.DETERMINISTIC
