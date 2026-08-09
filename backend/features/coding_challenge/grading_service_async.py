"""
Coding-challenge grading job — the scheduled (not request-handler) pipeline that
runs after /submit: stop/start power-cycle, hidden-test injection, test execution,
transcript/timeline harvest, AI-judged scoring, and cleanup.
"""
import difflib
import json
import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import update

from persistence.models.quiz import (
    CodeWorkspace, CodeSubmission, CodeSubmissionStatus, CodeWorkspaceStatus, Question,
    Quiz, CodingResultVisibility, GradingMode,
)
from features.coding_challenge import coder_client
from features.coding_challenge import static_analysis

logger = logging.getLogger(__name__)

# Scoring & Weightage Model — sums to 100.
#
# Revised 2026-08-09 (deterministic-first grading redesign, see
# _private/coding_challenge_grading_redesign_20260809.md): a fully AI-judged
# 65/100 with no calibration was producing near-100% scores regardless of
# actual outcome — confirmed live, a submission with functional_correctness=0
# (zero tests passing) still scored ai_usage_efficiency=100, architecture=100,
# code_quality=95, validation_discipline=95 from the same single ungrounded
# Gemini call. Two changes here:
#   - "proctoring" removed entirely — it was a pure stub always scored 100,
#     handing out 5 free points with zero signal behind them (DECIDED by user,
#     2026-08-09: redistribute its weight to functional_correctness rather
#     than leave it or spread it across the AI-judged criteria).
#   - "validation_discipline" moved from AI-judged to fully deterministic
#     (see _compute_validation_discipline below) — it's exactly the kind of
#     pattern-match (was an AI-authored commit followed by a test run before
#     the next one?) that doesn't need or benefit from LLM judgment, and
#     removing it cuts what has to go through the AI call at all.
_WEIGHTS = {
    "functional_correctness": 30,
    "ai_usage_efficiency": 20,
    "prompt_quality": 15,
    "validation_discipline": 15,
    "code_quality": 10,
    "architecture": 5,
    "time_taken": 5,
}

# DECIDED (user, 2026-08-09): a submission that fails almost all functional
# tests gets its overall score hard-capped, no matter how well the AI-judged
# "process" criteria score — directly fixes the exact case that prompted this
# redesign (0% tests passing, 70% overall score). This is a transparent,
# auditable rule, not another AI judgment call.
_FUNCTIONAL_FAILURE_THRESHOLD = 20   # functional_correctness score (0-100) below this...
_FUNCTIONAL_FAILURE_SCORE_CAP = 40   # ...caps the overall total at this, regardless of everything else

_TEST_COMMAND_RE = re.compile(
    r"\b(pytest|py\.test|mvn\s+(?:-\S+\s+)*test|gradle\s+test|npm\s+(?:run\s+)?test|"
    r"yarn\s+test|go\s+test|jest|rspec|dotnet\s+test|ctest)\b",
    re.IGNORECASE,
)
_GIT_COMMIT_HEADER_RE = re.compile(r"^commit ([0-9a-f]{7,40})")
_GIT_AUTHOR_EMAIL_RE = re.compile(r"^Author:.*<([^>]+)>")
_GIT_DATE_RE = re.compile(r"^Date:\s+(.+)$")
# AI-edit and manual-snapshot commit authors, matching main.tf's coder_agent
# startup_script exactly (the PostToolUse hook and swaya-snapshot-loop).
_AI_COMMIT_AUTHOR_EMAIL = "ai@swaya.local"
_CANDIDATE_COMMIT_AUTHOR_EMAIL = "candidate@swaya.local"

_SUREFIRE_SUMMARY_RE = re.compile(
    r"^Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)\s*$"
)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
_MAVEN_LOG_PREFIX_RE = re.compile(r"^\[(?:INFO|WARNING|ERROR)\]\s?")

# ── Deterministic-mode-only scoring (2026-08-09 grading-mode selector) ──────
# ai_usage_efficiency and prompt_quality's fully rule-based versions, used
# only when Question.grading_mode == DETERMINISTIC (Hybrid/AI-judged modes
# keep both AI-judged — see the plan's per-criterion table). Thresholds are
# a first-pass calibration, not yet validated against a broad set of real
# Deterministic-mode submissions (none exist yet, since the mode itself is
# new) — flagged explicitly in the plan as a "don't guess the direction, not
# just the magnitude" risk; retune once real data exists.
_NEAR_DUPLICATE_SIMILARITY_THRESHOLD = 0.82
_MIN_SUBSTANTIAL_AI_COMMITS = 2
_MIN_SUBSTANTIVE_PROMPT_WORDS = 6
_SPECIFICITY_MARKER_RE = re.compile(
    r"(`[^`]+`|\"[^\"]+\"|'[^']+'|\berror\b|\bexception\b|\bfunction\b|\bclass\b|"
    r"\btest\b|\bshould\b|\bmust\b|\bexpected\b|\bfails?\b|[A-Za-z_]+\(\)|\.[a-z_]+\()",
    re.IGNORECASE,
)


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


# ── Deterministic parsing of harvested data — added 2026-08-09 so
# validation_discipline no longer needs an LLM to eyeball it, and so the AI
# call for the criteria that DO stay AI-judged gets curated, bounded input
# instead of raw multi-megabyte dumps. All pure functions, no I/O, easily
# unit-testable against realistic fixture strings. ──────────────────────────

def _parse_git_date(date_str: str) -> Optional[datetime]:
    """`git log -p`'s default Date: line format, e.g. 'Sun Aug 9 04:40:12 2026 +0000'."""
    try:
        return datetime.strptime(date_str.strip(), "%a %b %d %H:%M:%S %Y %z")
    except ValueError:
        return None


def _parse_iso_timestamp(ts: str) -> Optional[datetime]:
    """Claude Code transcript timestamps are ISO 8601 with a trailing 'Z'
    (e.g. '2026-08-09T04:36:05.152Z') — Python's fromisoformat wants '+00:00'."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_git_commits(code_timeline: str) -> list[dict]:
    """Parses `git log -p` output into [{hash, author_email, date}], oldest-first
    (git log -p itself lists newest-first; this reverses so callers can walk
    forward through time). Tolerant of a missing Author:/Date: line on any
    given commit (author_email/date come back None) rather than raising —
    real `git log -p` output is what it is, not a format this owns."""
    commits = []
    current: Optional[dict] = None
    for line in (code_timeline or "").splitlines():
        m = _GIT_COMMIT_HEADER_RE.match(line)
        if m:
            if current:
                commits.append(current)
            current = {"hash": m.group(1), "author_email": None, "date": None}
            continue
        if current is None:
            continue
        m2 = _GIT_AUTHOR_EMAIL_RE.match(line)
        if m2:
            current["author_email"] = m2.group(1)
            continue
        m3 = _GIT_DATE_RE.match(line)
        if m3:
            current["date"] = _parse_git_date(m3.group(1))
            continue
    if current:
        commits.append(current)
    commits.reverse()  # oldest-first
    return commits


def _iter_transcript_entries(ai_transcript_raw: str):
    """Yields parsed JSON objects, one per real line — malformed lines skipped
    silently (the transcript format isn't a stable, documented API, matches
    the tolerance already established in _sum_token_usage)."""
    for line in (ai_transcript_raw or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _extract_test_run_timestamps(ai_transcript_raw: str) -> list[datetime]:
    """Timestamps of Bash tool_use calls whose command looks like a test run.
    Only test runs triggered through the AI chat are visible here — direct
    terminal use outside the chat leaves no trace in this transcript, an
    inherent limitation carried over from the original AI-judged prompt's own
    caveat, not new to this deterministic version."""
    timestamps = []
    for entry in _iter_transcript_entries(ai_transcript_raw):
        if entry.get("type") != "assistant":
            continue
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") != "Bash":
                continue
            command = (block.get("input") or {}).get("command", "")
            if _TEST_COMMAND_RE.search(command):
                ts = _parse_iso_timestamp(entry.get("timestamp", ""))
                if ts:
                    timestamps.append(ts)
    return sorted(timestamps)


def _extract_candidate_prompts(ai_transcript_raw: str) -> str:
    """Real human-typed prompts only — excludes tool_result 'user' entries
    (Claude Code logs a Bash tool's output as a 'user' message too, per the
    Anthropic Messages API convention; `origin.kind == "human"` is what
    actually distinguishes a real candidate keystroke from that) and all
    AI/tool output. This is what prompt_quality gets AI-judged against now,
    not the full raw transcript — smaller, and the LLM isn't being asked to
    pick the candidate's own words out of a haystack of tool noise itself."""
    prompts = []
    for entry in _iter_transcript_entries(ai_transcript_raw):
        if entry.get("type") != "user":
            continue
        if (entry.get("origin") or {}).get("kind") != "human":
            continue
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "").strip()
                if text:
                    prompts.append(text)
    return "\n---\n".join(prompts)


def _compute_usage_summary(code_timeline: str, ai_transcript_raw: str) -> dict:
    """Structured session stats — what ai_usage_efficiency gets AI-judged
    against now, instead of the raw transcript. Deliberately pre-digests the
    signals a human grader would actually look for (iteration pace, whether
    the candidate tested their own work) so the LLM is judging a compact
    summary, not doing the counting itself from scratch each time — cheaper,
    smaller, and more consistent across submissions."""
    commits = _parse_git_commits(code_timeline)
    ai_commits = [c for c in commits if c["author_email"] == _AI_COMMIT_AUTHOR_EMAIL]
    candidate_commits = [c for c in commits if c["author_email"] == _CANDIDATE_COMMIT_AUTHOR_EMAIL]
    test_runs = _extract_test_run_timestamps(ai_transcript_raw)
    human_prompts = [
        e for e in _iter_transcript_entries(ai_transcript_raw)
        if e.get("type") == "user" and (e.get("origin") or {}).get("kind") == "human"
    ]
    return {
        "total_human_prompts": len(human_prompts),
        "total_ai_driven_commits": len(ai_commits),
        "total_manual_snapshot_commits": len(candidate_commits),
        "total_test_runs_via_ai_chat": len(test_runs),
    }


def _compute_validation_discipline(code_timeline: str, ai_transcript_raw: str) -> int:
    """Fully deterministic (no LLM call) — moved off the AI-judged path
    2026-08-09. For each AI-authored commit, checks whether a test-run tool
    call happened in the window between that commit and the next one (or
    before submission, for the last commit): was the AI's work validated
    before being built on further? 100 when every AI-authored commit was
    followed by a validation run; scales down linearly from there.

    No AI-driven commits at all (candidate wrote everything by hand, or
    barely touched the AI) falls back to checking whether the candidate
    tested their own work at all — weaker signal, but not zero-information;
    scores 100/50 rather than a misleading 0."""
    commits = _parse_git_commits(code_timeline)
    test_runs = _extract_test_run_timestamps(ai_transcript_raw)

    ai_commits = [c for c in commits if c["author_email"] == _AI_COMMIT_AUTHOR_EMAIL and c["date"]]
    if not ai_commits:
        return 100 if test_runs else 50

    validated = 0
    for i, commit in enumerate(ai_commits):
        window_start = commit["date"]
        window_end = ai_commits[i + 1]["date"] if i + 1 < len(ai_commits) else None
        if any(
            ts >= window_start and (window_end is None or ts <= window_end)
            for ts in test_runs
        ):
            validated += 1
    return round(100 * validated / len(ai_commits))


def _count_near_duplicate_prompt_pairs(prompts: list[str]) -> int:
    """Consecutive-pair near-duplicate detection via stdlib difflib — a
    candidate re-asking essentially the same thing back-to-back is a real
    flailing signal (the AI didn't understand or fix it the first time).
    Deliberately NOT all-pairs (O(n^2)): two similar prompts far apart in a
    long session are a much weaker, noisier signal than the same thing
    twice in a row, and all-pairs would be needlessly expensive besides."""
    count = 0
    for a, b in zip(prompts, prompts[1:]):
        if difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= _NEAR_DUPLICATE_SIMILARITY_THRESHOLD:
            count += 1
    return count


def _compute_ai_usage_efficiency(code_timeline: str, ai_transcript_raw: str) -> tuple[int, str]:
    """Fully deterministic ai_usage_efficiency — Deterministic grading mode
    only (Hybrid keeps this criterion AI-judged, with these same signals as
    evidence rather than the score itself; see the grading-mode plan's
    per-criterion table).

    REVISED after checking real data (2026-08-09) — the first version of this
    function penalized a HIGH prompts-per-commit ratio, on the assumption
    that many prompts producing few commits meant flailing. Running it
    against real submissions showed that assumption was backwards: a real
    Claude-Code-driven session's normal pattern is a FEW prompts producing
    MANY autonomous commits (one real submission: 4 prompts -> 31 AI
    commits, scored 100 by the old AI-judged system) — the ratio this
    function checked essentially never occurs in practice, so it scored
    every real submission 100 regardless of input, zero discrimination. Real
    data also showed the old AI-judged system scored total non-engagement
    (0 prompts, 0 AI commits) as 0, not as a neutral N/A — this is presumably
    an assessment of AI-assisted coding skill specifically, so not using the
    assistant at all is a real 0, not something to spare.

    Current signals: total non-engagement -> 0; very few AI-authored commits
    (< _MIN_SUBSTANTIAL_AI_COMMITS) -> a real but weaker "minimal engagement"
    penalty (matches the one real low-commit submission checked: 1 AI
    commit, old score 70); consecutive near-duplicate prompts -> flailing
    penalty (sound on its own logic; no real submission checked exercised
    this path, so it remains unconfirmed against real data, unlike the
    other two signals above)."""
    commits = _parse_git_commits(code_timeline)
    ai_commits = [c for c in commits if c["author_email"] == _AI_COMMIT_AUTHOR_EMAIL]
    prompts_text = _extract_candidate_prompts(ai_transcript_raw)
    prompts = [p for p in prompts_text.split("\n---\n") if p.strip()]

    if not prompts and not ai_commits:
        return 0, "No AI engagement found — the assistant was not used at all."

    score = 100
    notes = []

    if len(ai_commits) < _MIN_SUBSTANTIAL_AI_COMMITS:
        score -= 25
        notes.append(f"only {len(ai_commits)} AI-authored commit(s) — minimal engagement")

    dup_pairs = _count_near_duplicate_prompt_pairs(prompts)
    if dup_pairs > 0:
        score -= min(30, dup_pairs * 10)
        notes.append(f"{dup_pairs} consecutive near-duplicate prompt(s) (re-asking without new information)")

    score = max(0, min(100, score))
    rationale = "Deterministic: " + (
        "; ".join(notes) if notes else "substantial AI-driven progress, no repeated prompts"
    ) + "."
    return score, rationale


def _compute_prompt_quality_heuristic(candidate_prompts: str) -> tuple[int, str]:
    """Best-effort heuristic proxy for Deterministic grading mode — NOT a
    real substitute for judging whether a prompt was actually clear, which
    genuinely requires understanding meaning and is exactly what no
    rule-based system can do fairly. DECIDED (user, 2026-08-09 "weigh in"
    round): score it anyway with surface signals rather than drop or
    redistribute the criterion, so all 7 criteria stay present in every
    mode — but this is deliberately the weakest, most gameable signal in the
    whole system, and the rationale text says so on every submission, not
    just in code comments."""
    prompts = [p for p in (candidate_prompts or "").split("\n---\n") if p.strip()]
    if not prompts:
        return 0, (
            "Heuristic proxy — approximates but does not replace human judgment of "
            "prompt clarity. No candidate prompts found."
        )

    word_counts = [len(p.split()) for p in prompts]
    avg_words = sum(word_counts) / len(word_counts)
    specific = sum(1 for p in prompts if _SPECIFICITY_MARKER_RE.search(p))
    specificity_rate = specific / len(prompts)

    score = 100
    notes = []
    if avg_words < _MIN_SUBSTANTIVE_PROMPT_WORDS:
        score -= 35
        notes.append(f"prompts average only {avg_words:.1f} words")
    elif avg_words < _MIN_SUBSTANTIVE_PROMPT_WORDS * 2:
        score -= 15
        notes.append(f"prompts average {avg_words:.1f} words — fairly terse")

    if specificity_rate < 0.3:
        score -= 30
        notes.append(f"only {specific}/{len(prompts)} prompts contain concrete specifics")
    elif specificity_rate < 0.6:
        score -= 10
        notes.append(f"{specific}/{len(prompts)} prompts contain concrete specifics")

    score = max(0, min(100, score))
    rationale = (
        "Heuristic proxy — approximates but does not replace human judgment of prompt "
        "clarity. " + ("; ".join(notes) if notes else "prompts are reasonably detailed and specific") + "."
    )
    return score, rationale


def _build_score_breakdown(
    ai_scores: dict, functional_correctness: int, time_taken: int,
    validation_discipline: int,
    weights: Optional[dict] = None,
) -> tuple[dict, int]:
    """Backend computes the final weighted score itself — never trusts the LLM
    to do the arithmetic. Returns (score_breakdown, ai_score).

    `weights` is the host's per-question override (Question.grading_weights),
    falling back to the platform default _WEIGHTS when not set — see
    schemas.py's GRADING_WEIGHT_CRITERIA, which mirrors _WEIGHTS' keys exactly.

    Applies the functional-failure score cap (DECIDED, user, 2026-08-09):
    a submission whose functional_correctness is below
    _FUNCTIONAL_FAILURE_THRESHOLD gets its overall total capped at
    _FUNCTIONAL_FAILURE_SCORE_CAP regardless of how well the AI-judged
    criteria scored — a transparent, auditable rule, not another AI call."""
    weights = weights or _WEIGHTS
    all_scores = {
        "functional_correctness": functional_correctness,
        "ai_usage_efficiency": ai_scores.get("ai_usage_efficiency", 0),
        "prompt_quality": ai_scores.get("prompt_quality", 0),
        "validation_discipline": validation_discipline,
        "code_quality": ai_scores.get("code_quality", 0),
        "architecture": ai_scores.get("architecture", 0),
        "time_taken": time_taken,
    }
    breakdown = {}
    total = 0.0
    for criterion, weight in weights.items():
        score = all_scores[criterion]
        contribution = score * weight / 100
        breakdown[criterion] = {"weight": weight, "score": score, "contribution": round(contribution, 2)}
        total += contribution
    final = round(total)
    if functional_correctness < _FUNCTIONAL_FAILURE_THRESHOLD:
        final = min(final, _FUNCTIONAL_FAILURE_SCORE_CAP)
    return breakdown, final


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
            # Final code as submitted — what code_quality/architecture are AI-judged
            # against now (2026-08-09 deterministic-first grading redesign), not a
            # reconstruction from code_timeline's diff history. `git ls-files`
            # respects the repo's own .gitignore (so a well-configured starter repo
            # naturally excludes node_modules/build output); `grep -Iq .` is the
            # portable binary-file skip (relies only on grep, not an external `file`
            # binary that may not be installed) — a binary sneaking through would risk
            # breaking the JSON request to Gemini with invalid UTF-8, not just wasting
            # space. `head -c` is a hard byte cap regardless, defense in depth on top
            # of the provider-side truncation in gemini.py.
            final_code_snapshot, _, _ = await coder_client.exec_in_workspace(
                workspace_name,
                "git ls-files | while IFS= read -r f; do "
                "if [ -f \"$f\" ] && grep -Iq . \"$f\" 2>/dev/null; then "
                "echo \"=== FILE: $f ===\"; cat \"$f\"; echo; "
                "fi; done | head -c 400000"
            )

            # Static analysis (2026-08-09 grading-mode selector) — harvested here,
            # while the workspace is still alive, regardless of the question's
            # grading_mode: cheap enough to always compute, and regrade_submission
            # has NO live workspace (its own docstring says so explicitly), so this
            # is the only place hybrid/deterministic mode's code_quality/architecture
            # input can ever come from. _run_ai_scoring must always read
            # submission.static_analysis_result, never call run_static_analysis
            # itself.
            language = _detect_language(test_command)
            static_analysis_result = await static_analysis.run_static_analysis(workspace_name, language)

            submission.test_output = test_output
            submission.passed_count = passed_count
            submission.total_count = total_count
            submission.ai_transcript_raw = transcript_raw
            submission.code_timeline = code_timeline
            submission.final_code_snapshot = final_code_snapshot
            submission.static_analysis_result = static_analysis_result
            submission.ai_token_usage = _sum_token_usage(transcript_raw)
        except Exception as e:
            logger.error("run_grading_job: harvest failed for submission %s: %s", submission_id, e)
            submission.status = CodeSubmissionStatus.FAILED
            submission.error_message = str(e)
            await db.commit()
            await _cleanup(db, workspace)
            return

        # ── Everything above is now harvested and safe — committed here, not left
        # as in-memory ORM attributes, so it survives even if _run_ai_scoring's own
        # commit later fails and falls back to its minimal raw UPDATE (which
        # deliberately excludes these fields — see that function's comment). Closes
        # a latent gap that predates this change: without this commit, a failure in
        # _run_ai_scoring's final commit would have silently discarded all harvested
        # data too, not just the AI scores, despite this comment already claiming
        # it was "safe". A failure from here on is genuinely recoverable
        # (partial_failed), not a total loss. ──────────────────────────────────
        await db.commit()
        await _run_ai_scoring(db, submission, workspace, question)
        await _cleanup(db, workspace)


async def _run_ai_scoring(db, submission: CodeSubmission, workspace: CodeWorkspace, question: Question) -> None:
    """Shared by the fresh-grading pipeline and the host-triggered regrade path
    (regrade_submission below) — scores an already-harvested submission (code_timeline
    + ai_transcript_raw + final_code_snapshot already persisted) and commits a
    terminal status. Does NOT touch the Coder workspace itself; caller decides
    whether cleanup is needed.

    Revised 2026-08-09 (deterministic-first grading redesign): validation_discipline
    is now computed here directly from the harvested data (_compute_validation_discipline),
    not asked of the LLM — it's always available even if the AI call itself fails,
    so a PARTIAL_FAILED submission still has a real validation_discipline score
    once regraded, not just the 4 AI-judged criteria.

    Further revised 2026-08-09 (grading-mode selector — see
    _private/coding_challenge_grading_mode_plan_20260809.md): dispatches
    code_quality/architecture/ai_usage_efficiency/prompt_quality per
    Question.grading_mode instead of always asking Gemini for all 4.
    Deterministic mode never calls the LLM at all; hybrid grounds the LLM
    call in the harvested static_analysis_result as evidence; ai_judged is
    today's original behavior, now with self-consistency (3-sample median)
    instead of a single call."""
    from core.ai.router import assess_coding_challenge_consistent

    # Resolved once and reused for both the AI call and the score combination below,
    # so what the model is told its weights are can never drift from what's actually
    # applied to compute the final score.
    weights = question.grading_weights or _WEIGHTS

    # Mode resolution — regrade reuses whatever was resolved on the original
    # attempt (grading_mode_used already set) so a host editing the question's
    # mode after candidates are graded doesn't silently change an in-flight
    # regrade's behavior; a genuine first pass falls through to the question's
    # current mode. Committed immediately, in its OWN transaction, separate
    # from the fragile final commit below (which has a documented real
    # failure history — see its own comment — and deliberately discards
    # everything except status/error_message/graded_at on failure) so this
    # resolution survives even if the rest of this function's work doesn't.
    resolved_mode = submission.grading_mode_used or question.grading_mode or GradingMode.HYBRID
    submission.grading_mode_used = resolved_mode
    await db.commit()

    code_timeline = submission.code_timeline or ""
    ai_transcript = submission.ai_transcript_raw or ""
    # Legacy fallback: submissions harvested before final_code_snapshot existed
    # (this migration, 2026-08-09) don't have one — fall back to the diff
    # history rather than showing the grader nothing at all. Only affects
    # already-harvested rows; every new submission gets a real snapshot.
    final_code_snapshot = submission.final_code_snapshot or code_timeline
    candidate_prompts = _extract_candidate_prompts(ai_transcript)
    usage_summary = _compute_usage_summary(code_timeline, ai_transcript)
    validation_discipline = _compute_validation_discipline(code_timeline, ai_transcript)
    # Read-only here, never (re-)computed — see run_grading_job's harvest
    # step and this function's docstring for why.
    static_analysis_result = submission.static_analysis_result

    ai_result = None
    last_error: Optional[Exception] = None

    if resolved_mode == GradingMode.DETERMINISTIC:
        # Zero LLM calls — fully rule-based, fully reproducible. Each
        # deterministic function already handles its own failure/fallback
        # internally (never raises), so this branch never lands in the
        # PARTIAL_FAILED path below the way the AI-judged branch can.
        _missing_analysis = {"failed": True, "reason": "no static analysis result available"}
        code_quality, code_quality_note = static_analysis._score_code_quality(
            static_analysis_result or _missing_analysis
        )
        architecture, architecture_note = static_analysis._score_architecture(
            static_analysis_result or _missing_analysis
        )
        ai_usage_efficiency, ai_usage_note = _compute_ai_usage_efficiency(code_timeline, ai_transcript)
        prompt_quality, prompt_quality_note = _compute_prompt_quality_heuristic(candidate_prompts)
        ai_result = {
            "code_quality": code_quality,
            "architecture": architecture,
            "ai_usage_efficiency": ai_usage_efficiency,
            "prompt_quality": prompt_quality,
            "rationale": "\n".join([code_quality_note, architecture_note, ai_usage_note, prompt_quality_note]),
        }
    else:
        # ai_judged / hybrid — both go through Gemini with self-consistency;
        # hybrid additionally grounds code_quality/architecture in the
        # harvested static analysis result as evidence (plan §2/§4/§7).
        static_analysis_evidence = static_analysis_result if resolved_mode == GradingMode.HYBRID else None
        for _attempt in range(2):  # one retry
            try:
                ai_result = await assess_coding_challenge_consistent(
                    question.text, question.grading_rubric or "",
                    final_code_snapshot, candidate_prompts, usage_summary,
                    weights, static_analysis_evidence,
                )
                break
            except Exception as e:
                last_error = e
                logger.warning(
                    "_run_ai_scoring: assess_coding_challenge_consistent attempt failed: %s", e
                )

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
        score_breakdown, ai_score = _build_score_breakdown(
            ai_result, functional_correctness, time_taken, validation_discipline, weights=weights
        )
        submission.score_breakdown = score_breakdown
        submission.ai_score = ai_score
        submission.ai_verdict = "pass" if ai_score >= 50 else "fail"
        submission.ai_rationale = ai_result.get("rationale", "")
        submission.status = CodeSubmissionStatus.GRADED
        submission.error_message = None

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
        logger.error("_run_ai_scoring: final commit failed for submission %s: %s", submission.id, e)
        await db.rollback()
        await db.execute(
            update(CodeSubmission)
            .where(CodeSubmission.id == submission.id)
            .values(
                status=CodeSubmissionStatus.PARTIAL_FAILED,
                error_message=f"grading computed but could not be persisted: {e}"[:2000],
                graded_at=datetime.utcnow(),
                # Belt-and-suspenders (grading_mode_used is already durably
                # committed earlier in this function, in its own transaction,
                # specifically so it survives this exact failure path — this
                # is redundant, not load-bearing, but cheap and harmless).
                grading_mode_used=submission.grading_mode_used,
            )
        )
        await db.commit()
        return

    if submission.status == CodeSubmissionStatus.GRADED:
        await _send_completion_email(db, submission, workspace, question)


async def _send_completion_email(db, submission: CodeSubmission, workspace: CodeWorkspace, question: Question) -> None:
    """Only fires for status_only/full visibility — in hidden mode the candidate is
    told upfront the host will follow up separately, so an automated email here
    would contradict that promise. Never fires for a failed grade; that's a system
    problem the host resolves quietly, not something the candidate is told about."""
    if question.result_visibility not in (CodingResultVisibility.STATUS_ONLY, CodingResultVisibility.FULL):
        return
    try:
        from core.auth.email_service import send_email
        from features.coding_challenge.coding_challenge_service_async import create_invite_token

        quiz = await db.get(Quiz, workspace.quiz_id)
        token = create_invite_token(workspace.quiz_id, question.id, workspace.candidate_email)
        import os
        frontend_url = os.getenv("FRONTEND_URL", "https://www.swaya.me")
        result_url = f"{frontend_url}/c/{token}"

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto">
          <h2 style="color:#1677ff">Your submission has been reviewed</h2>
          <p>Quiz: <strong>{quiz.title if quiz else ''}</strong></p>
          <p>Your coding challenge submission has finished processing.</p>
          <p><a href="{result_url}" style="display:inline-block;padding:10px 20px;background:#1677ff;
             color:#fff;border-radius:6px;text-decoration:none">View Your Result</a></p>
        </div>
        """
        await send_email(
            subject=f"Your submission has been reviewed — {quiz.title if quiz else 'Coding Challenge'}",
            recipients=[workspace.candidate_email],
            html_body=html_body,
        )
    except Exception as e:
        logger.warning("_send_completion_email: failed for submission %s: %s", submission.id, e)


async def regrade_submission(submission_id: int) -> bool:
    """Host-triggered recovery for a PARTIAL_FAILED submission (harvest succeeded,
    only the AI-scoring call failed) — re-scores using the already-persisted
    code_timeline/ai_transcript_raw. No workspace involved: it was already destroyed
    by _cleanup at the end of the original run_grading_job regardless of outcome.
    Returns False (no-op) if the submission isn't in a regradable state — a FAILED
    submission never harvested anything, so there is nothing to re-score."""
    from persistence.database_async import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        submission = await db.get(CodeSubmission, submission_id)
        if not submission or submission.status != CodeSubmissionStatus.PARTIAL_FAILED:
            return False
        workspace = await db.get(CodeWorkspace, submission.workspace_id)
        question = await db.get(Question, submission.question_id)
        if not workspace or not question:
            return False

        submission.status = CodeSubmissionStatus.GRADING
        await db.commit()

        await _run_ai_scoring(db, submission, workspace, question)
        return True
