"""
Unit tests for features.coding_challenge.grading_service_async: helper functions
(language detection, test-output parsing, token summation, deterministic scoring)
and the full run_grading_job pipeline's ordering, retry, and failure-mode behavior.
"""
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.coding_challenge import grading_service_async as gsvc
from persistence.models.quiz import (
    CodeWorkspace, CodeSubmission, CodeSubmissionStatus, CodeWorkspaceStatus, Question,
)


# ── _detect_language ─────────────────────────────────────────────────────────

def test_detect_language_defaults_to_python():
    assert gsvc._detect_language("pytest -q") == "python"
    assert gsvc._detect_language("") == "python"


def test_detect_language_detects_java():
    assert gsvc._detect_language("mvn test") == "java"
    assert gsvc._detect_language("./gradlew test") == "java"


# ── _run_tests (Python path) ─────────────────────────────────────────────────

def test_run_tests_python_parses_json_report():
    report = json.dumps({"summary": {"passed": 3, "total": 5}})

    async def fake_exec(workspace_name, command):
        if "--json-report" in command:
            return "3 failed, 2 passed... wait", None, 1
        if command.startswith("cat "):
            return report, None, 0
        raise AssertionError(f"unexpected command: {command}")

    with patch.object(gsvc.coder_client, "exec_in_workspace", fake_exec):
        test_output, passed, total = asyncio.run(gsvc._run_tests("ws-1", "pytest -q"))
    assert passed == 3
    assert total == 5


def test_run_tests_python_appends_json_report_flags():
    captured = []

    async def fake_exec(workspace_name, command):
        captured.append(command)
        if "--json-report" in command:
            return "", None, 0
        return json.dumps({"summary": {"passed": 0, "total": 0}}), None, 0

    with patch.object(gsvc.coder_client, "exec_in_workspace", fake_exec):
        asyncio.run(gsvc._run_tests("ws-1", "pytest -q"))
    assert "--json-report" in captured[0]
    assert "pytest -q" in captured[0]


def test_run_tests_python_handles_malformed_report():
    async def fake_exec(workspace_name, command):
        if "--json-report" in command:
            return "some output", None, 1
        return "not valid json{{{", None, 0

    with patch.object(gsvc.coder_client, "exec_in_workspace", fake_exec):
        test_output, passed, total = asyncio.run(gsvc._run_tests("ws-1", "pytest -q"))
    assert passed is None
    assert total is None


# ── _run_tests (Java / Surefire path) ────────────────────────────────────────

_SUREFIRE_OUTPUT = """
Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 - in org.junit.tests.SomeClassTest

Tests run: 2, Failures: 1, Errors: 0, Skipped: 0 - in org.junit.tests.OtherClassTest

Results:

Tests run: 5, Failures: 1, Errors: 0, Skipped: 0

[INFO] BUILD FAILURE
"""

# Byte-for-byte real `mvn test` output, captured during Phase 9.2's live
# end-to-end walkthrough (quiz 13/question 6, 2026-07-24) via the actual
# coder_client.exec_in_workspace path — not a hand-written approximation.
# Maven auto-detects color support even under a non-interactive `coder ssh`
# exec (ANSI escapes wrap tokens including the `Results:` header itself), and
# every line carries a `[INFO] ` prefix with no space before the colon
# (`[INFO] Results:`, not the bare `Results :` originally assumed).
_REAL_SUREFIRE_OUTPUT_WITH_ANSI = (
    "[\x1b[1;34mINFO\x1b[m] -------------------------------------------------------\n"
    "[\x1b[1;34mINFO\x1b[m]  T E S T S\n"
    "[\x1b[1;34mINFO\x1b[m] -------------------------------------------------------\n"
    "[\x1b[1;34mINFO\x1b[m] Running com.swaya.demo.\x1b[1mPalindromeCheckerTest\x1b[m\n"
    "[\x1b[1;34mINFO\x1b[m] \x1b[1;32mTests run: \x1b[0;1;32m3\x1b[m, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 0.064 s -- in com.swaya.demo.\x1b[1mPalindromeCheckerTest\x1b[m\n"
    "[\x1b[1;34mINFO\x1b[m] Running com.swaya.demo.\x1b[1mPalindromeCheckerHiddenTest\x1b[m\n"
    "[\x1b[1;34mINFO\x1b[m] \x1b[1;32mTests run: \x1b[0;1;32m3\x1b[m, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 0.015 s -- in com.swaya.demo.\x1b[1mPalindromeCheckerHiddenTest\x1b[m\n"
    "[\x1b[1;34mINFO\x1b[m] \n"
    "[\x1b[1;34mINFO\x1b[m] Results:\n"
    "[\x1b[1;34mINFO\x1b[m] \n"
    "[\x1b[1;34mINFO\x1b[m] \x1b[1;32mTests run: 6, Failures: 0, Errors: 0, Skipped: 0\x1b[m\n"
    "[\x1b[1;34mINFO\x1b[m] \n"
    "[\x1b[1;34mINFO\x1b[m] \x1b[1mBUILD SUCCESS\x1b[m\n"
)


def test_run_tests_java_parses_aggregate_not_per_class_subtotal():
    """The exact regression this must guard against: a naive first-match regex
    would grab the per-class subtotal (3 or 2) instead of the true aggregate (5)."""
    async def fake_exec(workspace_name, command):
        return _SUREFIRE_OUTPUT, None, 1

    with patch.object(gsvc.coder_client, "exec_in_workspace", fake_exec):
        test_output, passed, total = asyncio.run(gsvc._run_tests("ws-1", "mvn test"))
    assert total == 5
    assert passed == 4  # 5 - 1 failure - 0 errors - 0 skipped


def test_run_tests_java_parses_real_ansi_colored_maven_output():
    """Regression for the bug found in Phase 9.2's live walkthrough: real `mvn
    test` output (via coder_client.exec_in_workspace) carries ANSI escapes and a
    `[INFO] ` prefix on the `Results:` header and summary line, so a match
    against a bare 'Results :' silently never fires, leaving passed/total None
    despite a genuine BUILD SUCCESS with every test passing."""
    async def fake_exec(workspace_name, command):
        return _REAL_SUREFIRE_OUTPUT_WITH_ANSI, None, 0

    with patch.object(gsvc.coder_client, "exec_in_workspace", fake_exec):
        test_output, passed, total = asyncio.run(gsvc._run_tests("ws-1", "mvn test"))
    assert total == 6
    assert passed == 6


def test_run_tests_java_no_results_header_returns_none():
    async def fake_exec(workspace_name, command):
        return "some unrelated maven output\nBUILD FAILURE", None, 1

    with patch.object(gsvc.coder_client, "exec_in_workspace", fake_exec):
        _, passed, total = asyncio.run(gsvc._run_tests("ws-1", "mvn test"))
    assert passed is None
    assert total is None


# ── _sum_token_usage ─────────────────────────────────────────────────────────

def test_sum_token_usage_sums_across_turns():
    transcript = "\n".join([
        json.dumps({"message": {"usage": {"input_tokens": 100, "output_tokens": 50}}}),
        json.dumps({"message": {"usage": {"input_tokens": 200, "output_tokens": 80,
                                           "cache_read_input_tokens": 30}}}),
        "",  # blank line, should be skipped
        "not json at all",  # malformed, should be skipped
    ])
    totals = gsvc._sum_token_usage(transcript)
    assert totals["input_tokens"] == 300
    assert totals["output_tokens"] == 130
    assert totals["cache_read_input_tokens"] == 30
    assert totals["turns"] == 2


def test_sum_token_usage_empty_transcript():
    totals = gsvc._sum_token_usage("")
    assert totals["turns"] == 0
    assert totals["input_tokens"] == 0


# ── Deterministic scoring ────────────────────────────────────────────────────

def test_functional_correctness_computation():
    assert gsvc._compute_functional_correctness(5, 5) == 100
    assert gsvc._compute_functional_correctness(0, 5) == 0
    assert gsvc._compute_functional_correctness(3, 5) == 60
    assert gsvc._compute_functional_correctness(None, None) == 0
    assert gsvc._compute_functional_correctness(None, 0) == 0


def test_time_taken_full_credit_at_or_under_budget():
    start = datetime(2026, 1, 1, 0, 0, 0)
    on_time = start + timedelta(seconds=300)
    assert gsvc._compute_time_taken(start, on_time, 300) == 100
    early = start + timedelta(seconds=100)
    assert gsvc._compute_time_taken(start, early, 300) == 100


def test_time_taken_linear_decay_to_zero_at_double_budget():
    start = datetime(2026, 1, 1, 0, 0, 0)
    double_budget = start + timedelta(seconds=600)  # 2x a 300s budget
    assert gsvc._compute_time_taken(start, double_budget, 300) == 0
    halfway_over = start + timedelta(seconds=450)  # 150s over a 300s budget = 50% decay
    assert gsvc._compute_time_taken(start, halfway_over, 300) == 50


def test_time_taken_unset_budget_always_full_credit():
    start = datetime(2026, 1, 1, 0, 0, 0)
    way_later = start + timedelta(hours=10)
    assert gsvc._compute_time_taken(start, way_later, None) == 100


def test_build_score_breakdown_weights_sum_to_100():
    assert sum(gsvc._WEIGHTS.values()) == 100


def test_build_score_breakdown_computes_correct_weighted_total():
    ai_scores = {
        "ai_usage_efficiency": 80, "prompt_quality": 80, "validation_discipline": 80,
        "code_quality": 80, "architecture": 80,
    }
    breakdown, ai_score = gsvc._build_score_breakdown(ai_scores, functional_correctness=100, time_taken=100)
    # 100*.25 + 80*.20 + 80*.15 + 80*.15 + 80*.10 + 80*.05 + 100*.05 + 100*.05
    expected = 100 * .25 + 80 * .20 + 80 * .15 + 80 * .15 + 80 * .10 + 80 * .05 + 100 * .05 + 100 * .05
    assert ai_score == round(expected)
    assert breakdown["proctoring"]["score"] == 100  # stubbed at full credit
    assert breakdown["functional_correctness"]["weight"] == 25


# ── Full pipeline: fixtures/mocks ───────────────────────────────────────────

def _fixture_submission(status=CodeSubmissionStatus.QUEUED) -> CodeSubmission:
    return CodeSubmission(
        id=1, workspace_id=1, question_id=10, status=status,
        submitted_at=datetime(2026, 1, 1, 0, 10, 0),
    )


def _fixture_workspace() -> CodeWorkspace:
    return CodeWorkspace(
        id=1, tenant_id=1, quiz_id=1, question_id=10, candidate_email="a@b.com",
        ide_type="code_server", coder_workspace_name="ws-1",
        created_at=datetime(2026, 1, 1, 0, 0, 0),
    )


def _fixture_question(hidden_test=False) -> Question:
    kwargs = dict(
        id=10, quiz_id=1, question_type="coding_challenge", text="Solve it", order=0,
        test_command="pytest -q", grading_rubric="Be correct",
    )
    if hidden_test:
        kwargs["hidden_test_content"] = "def test_hidden(): pass"
        kwargs["hidden_test_filename"] = "test_hidden.py"
    return Question(**kwargs)


def _mock_session(submission, workspace, question):
    db = AsyncMock()
    db.get = AsyncMock(side_effect=[submission, workspace, question])
    db.commit = AsyncMock()
    session_cls = MagicMock()
    session_cls.return_value.__aenter__ = AsyncMock(return_value=db)
    session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return session_cls, db


# ── _cleanup ─────────────────────────────────────────────────────────────────

def test_cleanup_marks_workspace_destroyed_after_successful_delete():
    """Regression for the gap found in Phase 9.2's live walkthrough: delete_workspace
    genuinely removed the real Coder resource, but nothing ever set the DB row's
    status to DESTROYED, leaving it stuck at SUBMITTED forever."""
    workspace = _fixture_workspace()
    db = AsyncMock()
    db.commit = AsyncMock()

    with patch.object(gsvc.coder_client, "delete_workspace", AsyncMock()), \
         patch("features.coding_challenge.coding_challenge_service_async.cancel_lifetime_cap_job"):
        asyncio.run(gsvc._cleanup(db, workspace))

    assert workspace.status == CodeWorkspaceStatus.DESTROYED
    db.commit.assert_called_once()


def test_cleanup_leaves_status_unset_when_delete_workspace_fails():
    workspace = _fixture_workspace()
    db = AsyncMock()
    db.commit = AsyncMock()

    with patch.object(gsvc.coder_client, "delete_workspace",
                       AsyncMock(side_effect=Exception("coder delete broken"))), \
         patch("features.coding_challenge.coding_challenge_service_async.cancel_lifetime_cap_job"):
        asyncio.run(gsvc._cleanup(db, workspace))

    assert workspace.status != CodeWorkspaceStatus.DESTROYED
    db.commit.assert_not_called()


# ── Ordering guard ───────────────────────────────────────────────────────────

def test_grading_job_ordering_stop_start_hidden_test_then_exec():
    """Confirms actual CALL ORDER, not just that each step happened somewhere."""
    submission = _fixture_submission()
    workspace = _fixture_workspace()
    question = _fixture_question(hidden_test=True)
    session_cls, db = _mock_session(submission, workspace, question)

    call_order = []

    def track(name):
        async def _inner(*args, **kwargs):
            call_order.append(name)
            if name == "exec_in_workspace":
                cmd = args[1] if len(args) > 1 else kwargs.get("command", "")
                if "--json-report" in cmd:
                    return "", None, 0
                if cmd.startswith("cat /tmp"):
                    return json.dumps({"summary": {"passed": 1, "total": 1}}), None, 0
                return "transcript-or-timeline-output", None, 0
        return _inner

    with patch("persistence.database_async.AsyncSessionLocal", session_cls), \
         patch.object(gsvc.coder_client, "stop_workspace", track("stop_workspace")), \
         patch.object(gsvc.coder_client, "start_workspace", track("start_workspace")), \
         patch.object(gsvc.coder_client, "write_file_to_workspace", track("write_file_to_workspace")), \
         patch.object(gsvc.coder_client, "exec_in_workspace", track("exec_in_workspace")), \
         patch.object(gsvc.coder_client, "delete_workspace", AsyncMock()), \
         patch("core.ai.router.assess_coding_challenge",
               AsyncMock(return_value={"ai_usage_efficiency": 50, "prompt_quality": 50,
                                        "validation_discipline": 50, "code_quality": 50,
                                        "architecture": 50, "rationale": "ok"})), \
         patch.object(gsvc, "_cleanup", AsyncMock()):
        asyncio.run(gsvc.run_grading_job(1))

    # stop -> start -> hidden-test write -> exec (repeated for test/transcript/timeline)
    assert call_order[0] == "stop_workspace"
    assert call_order[1] == "start_workspace"
    assert call_order[2] == "write_file_to_workspace"
    assert call_order[3] == "exec_in_workspace"
    assert all(c == "exec_in_workspace" for c in call_order[4:])


# ── Retry-then-partial_failed path ──────────────────────────────────────────

def test_grading_job_retries_once_then_partial_failed_with_data_intact():
    submission = _fixture_submission()
    workspace = _fixture_workspace()
    question = _fixture_question()
    session_cls, db = _mock_session(submission, workspace, question)

    async def fake_exec(workspace_name, command):
        if "--json-report" in command:
            return "test output here", None, 0
        if command.startswith("cat /tmp"):
            return json.dumps({"summary": {"passed": 4, "total": 5}}), None, 0
        if "jsonl" in command:
            return json.dumps({"message": {"usage": {"input_tokens": 10, "output_tokens": 5}}}), None, 0
        return "git log output", None, 0

    call_count = {"n": 0}

    async def failing_assess(*args, **kwargs):
        call_count["n"] += 1
        raise RuntimeError("Gemini unreachable")

    with patch("persistence.database_async.AsyncSessionLocal", session_cls), \
         patch.object(gsvc.coder_client, "stop_workspace", AsyncMock()), \
         patch.object(gsvc.coder_client, "start_workspace", AsyncMock()), \
         patch.object(gsvc.coder_client, "exec_in_workspace", fake_exec), \
         patch.object(gsvc.coder_client, "delete_workspace", AsyncMock()), \
         patch("core.ai.router.assess_coding_challenge", failing_assess), \
         patch.object(gsvc, "_cleanup", AsyncMock()) as mock_cleanup:
        asyncio.run(gsvc.run_grading_job(1))

    assert call_count["n"] == 2  # exactly one retry
    assert submission.status == CodeSubmissionStatus.PARTIAL_FAILED
    assert "Gemini unreachable" in submission.error_message
    # everything already harvested must survive intact
    assert submission.test_output == "test output here"
    assert submission.passed_count == 4
    assert submission.total_count == 5
    assert submission.code_timeline == "git log output"
    assert submission.score_breakdown is None
    assert submission.ai_score is None
    mock_cleanup.assert_called_once()  # cleanup still runs even on partial failure


# ── Pre-harvest-failure path ─────────────────────────────────────────────────

def test_grading_job_pre_harvest_failure_persists_plain_failed():
    """A failure in stop_workspace itself (before anything is harvested) has
    nothing to salvage — status=failed, not partial_failed, and the AI is never
    even called."""
    submission = _fixture_submission()
    workspace = _fixture_workspace()
    question = _fixture_question()
    session_cls, db = _mock_session(submission, workspace, question)

    with patch("persistence.database_async.AsyncSessionLocal", session_cls), \
         patch.object(gsvc.coder_client, "stop_workspace", AsyncMock(side_effect=Exception("coder ssh broken"))), \
         patch.object(gsvc.coder_client, "exec_in_workspace", AsyncMock()) as mock_exec, \
         patch("core.ai.router.assess_coding_challenge", AsyncMock()) as mock_assess, \
         patch.object(gsvc, "_cleanup", AsyncMock()) as mock_cleanup:
        asyncio.run(gsvc.run_grading_job(1))

    assert submission.status == CodeSubmissionStatus.FAILED
    assert "coder ssh broken" in submission.error_message
    mock_exec.assert_not_called()
    mock_assess.assert_not_called()
    assert submission.test_output is None
    mock_cleanup.assert_called_once()  # still cleans up even on total pre-harvest failure


def test_grading_job_success_path_persists_graded_with_full_breakdown():
    submission = _fixture_submission()
    workspace = _fixture_workspace()
    question = _fixture_question()
    session_cls, db = _mock_session(submission, workspace, question)

    async def fake_exec(workspace_name, command):
        if "--json-report" in command:
            return "", None, 0
        if command.startswith("cat /tmp"):
            return json.dumps({"summary": {"passed": 5, "total": 5}}), None, 0
        return "output", None, 0

    with patch("persistence.database_async.AsyncSessionLocal", session_cls), \
         patch.object(gsvc.coder_client, "stop_workspace", AsyncMock()), \
         patch.object(gsvc.coder_client, "start_workspace", AsyncMock()), \
         patch.object(gsvc.coder_client, "exec_in_workspace", fake_exec), \
         patch.object(gsvc.coder_client, "delete_workspace", AsyncMock()), \
         patch("core.ai.router.assess_coding_challenge",
               AsyncMock(return_value={"ai_usage_efficiency": 90, "prompt_quality": 90,
                                        "validation_discipline": 90, "code_quality": 90,
                                        "architecture": 90, "rationale": "excellent"})), \
         patch.object(gsvc, "_cleanup", AsyncMock()):
        asyncio.run(gsvc.run_grading_job(1))

    assert submission.status == CodeSubmissionStatus.GRADED
    assert submission.ai_score is not None
    assert submission.ai_verdict == "pass"
    assert submission.score_breakdown is not None
    assert submission.graded_at is not None
