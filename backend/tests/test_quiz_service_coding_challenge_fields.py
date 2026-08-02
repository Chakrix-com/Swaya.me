"""
Regression test: quiz_service_async.QuizBuilderServiceAsync._to_quiz_response's
nested QuestionResponse construction dropped the 5 coding-challenge fields
(git_repo_url, test_command, hidden_test_content, hidden_test_filename,
time_budget_seconds) entirely -- a third, independent occurrence of the same
gap already fixed once in question_service_async.py's own _to_question_response
(see commit 432959e) and missed here because it's a separate manual
QuestionResponse(...) construction in a different file. Found live via a real
GET /quizzes/{id} (and the /publish response, which reuses the same
serializer) returning null for every one of these fields despite the DB row
being fully intact.
"""
from datetime import datetime
from unittest.mock import MagicMock

from features.quiz.quiz_service_async import QuizBuilderServiceAsync
from persistence.models.quiz import Quiz, QuizType, QuizStatus, TemplateScope, Question, QuestionType


def _fixture_quiz_with_coding_challenge_question() -> Quiz:
    question = Question(
        id=8, quiz_id=15, question_type=QuestionType.CODING_CHALLENGE, text="Solve it", order=0,
        points=1,
        git_repo_url="https://github.com/x/y", test_command="mvn test",
        hidden_test_content="hidden test source", hidden_test_filename="src/test/Hidden.java",
        time_budget_seconds=1800,
    )
    quiz = Quiz(
        id=15, event_id=15, tenant_id=1, title="Q", quiz_type=QuizType.CODING_CHALLENGE,
        status=QuizStatus.READY, is_template=False, template_scope=TemplateScope.TENANT,
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )
    quiz.__dict__["questions"] = [question]
    quiz.__dict__["folder"] = None
    return quiz


def test_to_quiz_response_includes_coding_challenge_fields():
    service = QuizBuilderServiceAsync(tier_service=MagicMock())
    quiz = _fixture_quiz_with_coding_challenge_question()

    response = service._to_quiz_response(quiz)

    q = response.questions[0]
    assert q.git_repo_url == "https://github.com/x/y"
    assert q.test_command == "mvn test"
    assert q.hidden_test_content == "hidden test source"
    assert q.hidden_test_filename == "src/test/Hidden.java"
    assert q.time_budget_seconds == 1800
