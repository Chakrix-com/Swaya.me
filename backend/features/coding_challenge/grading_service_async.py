"""
Coding-challenge grading job — the scheduled (not request-handler) pipeline that
runs after /submit: stop/start power-cycle, hidden-test injection, test execution,
transcript/timeline harvest, AI-judged scoring, and cleanup.
"""
import json
import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import update

from persistence.models.quiz import (
    CodeWorkspace, CodeSubmission, CodeSubmissionStatus, CodeWorkspaceStatus, Question,
)
from features.coding_challenge import coder_client

logger = logging.getLogger(__name__)

# Scoring & Weightage Model (adapted from SRS §17.2) — sums to 100
_WEIGHTS = {
    "functional_correctness": 25,
    "ai_usage_efficiency": 20,
    "prompt_quality": 15,
    "validation_discipline": 15,
    "code_quality": 10,
    "architecture": 5,
    "time_taken": 5,
    "proctoring": 5,
}

_SUREFIRE_SUMMARY_RE = re.compile(
    r"^Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)\s*$"
)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
_MAVEN_LOG_PREFIX_RE = re.compile(r"^\[(?:INFO|WARNING|ERROR)\]\s?")


def _clean_maven_line(line: str) -> str:
    """Maven auto-detects color support even under a non-interactive `coder ssh`
    exec, wrapping tokens (including the `Results:` header itself) in ANSI escape
    codes, and every line — `Results:` included — carries a `[INFO]/[WARNING]/[ERROR] `
    level prefix with no space before the colon. Confirmed against real `mvn test`
    output during Phase 9.2's live walkthrough (quiz 13/question 6) — matching a
    bare 'Results :' (as originally assumed) never fires against it."""
    return _MAVEN_LOG_PREFIX_RE.sub("", _ANSI_ESCAPE_RE.sub("", line)).strip()


def _detect_language(test_command: str) -> str:
    """No explicit language field on Question — the host's test_command itself is
    the only signal. Defaults to python (matches Question.test_command's own
    default of 'pytest -q')."""
    cmd_lower = (test_command or "").lower()
    if "mvn" in cmd_lower or "gradle" in cmd_lower:
        return "java"
    return "python"


async def _run_tests(workspace_name: str, test_command: str) -> tuple[str, Optional[int], Optional[int]]:
    """Runs test_command, returns (test_output, passed_count, total_count).
    Python: appends --json-report flags, parses the structured report.
    Java: parses the Surefire aggregate summary line (the one immediately after a
    bare 'Results :' line — confirmed during Phase 1 spikes that the same line
    format also appears once per test class, so a naive first-match would grab a
    per-class subtotal instead of the true total)."""
    language = _detect_language(test_command)

    if language == "python":
        report_path = "/tmp/coding_challenge_report.json"
        full_command = f"{test_command} --json-report --json-report-file={report_path}"
        test_output, _, _ = await coder_client.exec_in_workspace(workspace_name, full_command)
        report_raw, _, _ = await coder_client.exec_in_workspace(workspace_name, f"cat {report_path}")
        try:
            report = json.loads(report_raw)
            summary = report.get("summary", {})
            return test_output, summary.get("passed", 0), summary.get("total", 0)
        except (json.JSONDecodeError, AttributeError):
            logger.warning("_run_tests: could not parse pytest json-report for %s", workspace_name)
            return test_output, None, None

    # Java
    test_output, _, _ = await coder_client.exec_in_workspace(workspace_name, test_command)
    lines = test_output.splitlines()
    for i, line in enumerate(lines):
        if _clean_maven_line(line) == "Results:":
            for candidate in lines[i + 1:]:
                match = _SUREFIRE_SUMMARY_RE.match(_clean_maven_line(candidate))
                if match:
                    total, failures, errors, skipped = (int(x) for x in match.groups())
                    return test_output, total - failures - errors - skipped, total
    return test_output, None, None


def _sum_token_usage(ai_transcript_raw: str) -> dict:
    """Sums per-turn `usage` fields from Claude Code's JSONL transcript. Tolerant of
    malformed/partial lines — the transcript format isn't a stable, documented API."""
    totals = {
        "input_tokens": 0, "output_tokens": 0,
        "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
    }
    turns = 0
    for line in (ai_transcript_raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = (entry.get("message") or {}).get("usage") or entry.get("usage")
        if not isinstance(usage, dict):
            continue
        turns += 1
        for key in totals:
            value = usage.get(key)
            if isinstance(value, (int, float)):
                totals[key] += int(value)
    totals["turns"] = turns
    return totals


def _compute_functional_correctness(passed_count: Optional[int], total_count: Optional[int]) -> int:
    """Deterministic — never LLM-judged."""
    if not total_count:
        return 0
    return round(100 * (passed_count or 0) / total_count)


def _compute_time_taken(created_at: datetime, submitted_at: datetime,
                         time_budget_seconds: Optional[int]) -> int:
    """Full credit at/under budget; linear decay to 0 at 2x budget. Unset budget
    always scores full credit."""
    if not time_budget_seconds:
        return 100
    duration = (submitted_at - created_at).total_seconds()
    if duration <= time_budget_seconds:
        return 100
    return max(0, round(100 * (1 - (duration - time_budget_seconds) / time_budget_seconds)))


def _build_score_breakdown(ai_scores: dict, functional_correctness: int, time_taken: int) -> tuple[dict, int]:
    """Backend computes the final weighted score itself — never trusts the LLM
    to do the arithmetic. Returns (score_breakdown, ai_score)."""
    all_scores = {
        "functional_correctness": functional_correctness,
        "ai_usage_efficiency": ai_scores.get("ai_usage_efficiency", 0),
        "prompt_quality": ai_scores.get("prompt_quality", 0),
        "validation_discipline": ai_scores.get("validation_discipline", 0),
        "code_quality": ai_scores.get("code_quality", 0),
        "architecture": ai_scores.get("architecture", 0),
        "time_taken": time_taken,
        "proctoring": 100,  # stubbed at full credit — no proctoring integration in this MVP
    }
    breakdown = {}
    total = 0.0
    for criterion, weight in _WEIGHTS.items():
        score = all_scores[criterion]
        contribution = score * weight / 100
        breakdown[criterion] = {"weight": weight, "score": score, "contribution": round(contribution, 2)}
        total += contribution
    return breakdown, round(total)


async def _cleanup(db, workspace: CodeWorkspace) -> None:
    """Cancels the now-unneeded lifetime-cap job and deletes the workspace — always
    runs at the end of the pipeline regardless of which outcome (graded/
    partial_failed/failed) was reached. Marks the row DESTROYED only once the real
    Coder resource is confirmed gone — found via Phase 9.2's live walkthrough that
    this status update was previously missing entirely, leaving every workspace row
    stuck at SUBMITTED in the DB forever even after `coder list` showed it deleted."""
    from features.coding_challenge.coding_challenge_service_async import cancel_lifetime_cap_job
    workspace_name = workspace.coder_workspace_name
    cancel_lifetime_cap_job(workspace_name)
    try:
        await coder_client.delete_workspace(workspace_name)
        workspace.status = CodeWorkspaceStatus.DESTROYED
        await db.commit()
    except Exception as e:
        logger.warning("_cleanup: delete_workspace(%s) failed: %s", workspace_name, e)


async def run_grading_job(submission_id: int) -> None:
    """The scheduled grading job. Ordering is load-bearing (see the design doc's
    Hidden test injection section): stop -> start -> hidden-test write -> exec ->
    transcript harvest -> timeline harvest -> AI scoring -> cleanup."""
    from persistence.database_async import AsyncSessionLocal
    from core.ai.router import assess_coding_challenge

    async with AsyncSessionLocal() as db:
        submission = await db.get(CodeSubmission, submission_id)
        if not submission:
            logger.warning("run_grading_job: submission %s not found", submission_id)
            return
        workspace = await db.get(CodeWorkspace, submission.workspace_id)
        question = await db.get(Question, submission.question_id)
        if not workspace or not question:
            submission.status = CodeSubmissionStatus.FAILED
            submission.error_message = "workspace or question no longer exists"
            await db.commit()
            return

        submission.status = CodeSubmissionStatus.GRADING
        await db.commit()

        workspace_name = workspace.coder_workspace_name

        # ── Harvest half (6.6a) — a failure here has nothing to salvage ──────────
        try:
            await coder_client.stop_workspace(workspace_name)
            await coder_client.start_workspace(workspace_name)

            if question.hidden_test_content and question.hidden_test_filename:
                await coder_client.write_file_to_workspace(
                    workspace_name, question.hidden_test_filename, question.hidden_test_content
                )

            test_command = question.test_command or "pytest -q"
            test_output, passed_count, total_count = await _run_tests(workspace_name, test_command)

            transcript_raw, _, _ = await coder_client.exec_in_workspace(
                workspace_name, "cat ~/.claude/projects/*/*.jsonl 2>/dev/null || true"
            )
            code_timeline, _, _ = await coder_client.exec_in_workspace(workspace_name, "git log -p")

            submission.test_output = test_output
            submission.passed_count = passed_count
            submission.total_count = total_count
            submission.ai_transcript_raw = transcript_raw
            submission.code_timeline = code_timeline
            submission.ai_token_usage = _sum_token_usage(transcript_raw)
        except Exception as e:
            logger.error("run_grading_job: harvest failed for submission %s: %s", submission_id, e)
            submission.status = CodeSubmissionStatus.FAILED
            submission.error_message = str(e)
            await db.commit()
            await _cleanup(db, workspace)
            return

        # ── Everything above is now harvested and safe — a failure from here on is
        # recoverable (partial_failed), not a total loss ────────────────────────
        ai_result = None
        last_error: Optional[Exception] = None
        for _attempt in range(2):  # one retry
            try:
                ai_result = await assess_coding_challenge(
                    question.text, question.grading_rubric or "",
                    submission.code_timeline or "", submission.ai_transcript_raw or "",
                )
                break
            except Exception as e:
                last_error = e
                logger.warning("run_grading_job: assess_coding_challenge attempt failed: %s", e)

        functional_correctness = _compute_functional_correctness(
            submission.passed_count, submission.total_count
        )
        time_taken = _compute_time_taken(
            workspace.created_at, submission.submitted_at or datetime.utcnow(), question.time_budget_seconds
        )

        if ai_result is None:
            submission.status = CodeSubmissionStatus.PARTIAL_FAILED
            submission.error_message = str(last_error)
        else:
            score_breakdown, ai_score = _build_score_breakdown(ai_result, functional_correctness, time_taken)
            submission.score_breakdown = score_breakdown
            submission.ai_score = ai_score
            submission.ai_verdict = "pass" if ai_score >= 50 else "fail"
            submission.ai_rationale = ai_result.get("rationale", "")
            submission.status = CodeSubmissionStatus.GRADED

        submission.graded_at = datetime.utcnow()
        try:
            await db.commit()
        except Exception as e:
            # The one commit in this job with no earlier try/except around it — found
            # live (Phase 11) when a real, non-quiet `mvn test` run's ANSI-colored
            # output exceeded test_output's old TEXT cap, crashing this exact commit
            # and stranding the submission at `grading` forever (nothing upstream
            # ever sets a terminal status on this path). Root cause fixed by widening
            # the column, but this commit itself still had no failure handling at
            # all — a persistence failure here must still reach a terminal status,
            # never leave the row stuck, per this feature's own EV-6 principle. Falls
            # back to a minimal raw UPDATE that excludes the large harvested fields,
            # since those are the most likely cause of a repeat failure.
            logger.error("run_grading_job: final commit failed for submission %s: %s", submission_id, e)
            await db.rollback()
            await db.execute(
                update(CodeSubmission)
                .where(CodeSubmission.id == submission_id)
                .values(
                    status=CodeSubmissionStatus.PARTIAL_FAILED,
                    error_message=f"grading computed but could not be persisted: {e}"[:2000],
                    graded_at=datetime.utcnow(),
                )
            )
            await db.commit()
            await _cleanup(db, workspace)
            return

        await _cleanup(db, workspace)
