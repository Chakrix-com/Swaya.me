"""
Static analysis for hybrid/deterministic grading mode (2026-08-09 grading-mode
selector — see _private/coding_challenge_grading_mode_plan_20260809.md §2).

run_static_analysis MUST be called only from run_grading_job's harvest step,
while the candidate's workspace is still alive — regrade_submission has NO
live workspace (its own docstring says so explicitly), so this module's exec
calls can never run there. The result is persisted once to
CodeSubmission.static_analysis_result and read from that column forever
after; grading_service_async.py's _run_ai_scoring must never call this module
directly, only read the already-harvested column.

Uses `lizard` (language-agnostic complexity/length metrics — works on both
Python and Java without needing either project to actually build) and `ruff`
(Python-only lint). Java submissions get a weaker code_quality signal as a
result — a known, disclosed asymmetry (see the plan's Costs & risks
section), not something this module tries to paper over.
"""
import json
import logging
from typing import Optional

from features.coding_challenge import coder_client

logger = logging.getLogger(__name__)

_ANALYSIS_TIMEOUT_SECONDS = 60.0

# Thresholds — named constants in one place so they're easy to retune
# platform-wide as real score distributions come in. These can't account for
# per-problem difficulty (a legitimately harder problem needing bigger,
# more-branching functions scores the same as a trivial one) — the sharpest
# "deterministic != fair" edge in the whole redesign, disclosed rather than
# solved. See the plan's 8th review pass.
_COMPLEXITY_OK = 10
_COMPLEXITY_BAD = 20
_FUNCTION_LENGTH_OK = 60
_FUNCTION_LENGTH_BAD = 150
_LINT_VIOLATIONS_PER_FUNCTION_OK = 0.15
_LINT_VIOLATIONS_PER_FUNCTION_BAD = 0.6

# Punitive-neutral fallback score when analysis fails/is unavailable — NOT a
# flat "average" 50, deliberately (8th review-pass finding, plan §7/§8): a
# reassuring mid-range default is a gaming incentive, since a candidate whose
# real code would score below this has an incentive to crash or hang the
# analyzer on purpose rather than submit honestly-weak code.
_FALLBACK_SCORE = 28


async def run_static_analysis(workspace_name: str, language: str) -> dict:
    """Returns {avg_complexity, max_complexity, avg_function_length,
    longest_function, function_count, lint_violation_count, failed, reason}.
    lint_violation_count is None for non-Python languages (no ruff run) or if
    ruff itself failed — that's a softer, non-fatal degradation, distinct
    from `failed: True` which means lizard itself produced nothing usable and
    the whole analysis must be treated as punitive-neutral, not average.
    Never raises."""
    try:
        lizard_out, _, _ = await coder_client.exec_in_workspace(
            workspace_name, "lizard . --csv 2>/dev/null", timeout=_ANALYSIS_TIMEOUT_SECONDS,
        )
    except Exception as e:
        logger.warning("run_static_analysis: lizard exec failed for %s: %s", workspace_name, e)
        return _failed_result(f"lizard exec failed: {e}")

    metrics = _parse_lizard_csv(lizard_out)
    if metrics is None:
        return _failed_result(
            "lizard produced no parseable output (binary missing, timed out, "
            "or no analyzable source files)"
        )

    lint_violation_count = None
    if language == "python":
        try:
            ruff_out, _, _ = await coder_client.exec_in_workspace(
                workspace_name, "ruff check . --output-format=json 2>/dev/null",
                timeout=_ANALYSIS_TIMEOUT_SECONDS,
            )
            lint_violation_count = _parse_ruff_json(ruff_out)
        except Exception as e:
            logger.warning("run_static_analysis: ruff exec failed for %s: %s", workspace_name, e)
            # Non-fatal — code_quality degrades to the lizard-only signal
            # rather than failing the whole analysis, same as the
            # by-design Java gap below.

    return {
        **metrics,
        "lint_violation_count": lint_violation_count,
        "failed": False,
        "reason": None,
    }


def _failed_result(reason: str) -> dict:
    return {
        "avg_complexity": None, "max_complexity": None,
        "avg_function_length": None, "longest_function": None,
        "function_count": 0, "lint_violation_count": None,
        "failed": True, "reason": reason,
    }


def _parse_lizard_csv(raw: str) -> Optional[dict]:
    """lizard --csv columns: NLOC,CCN,token,PARAM,length,location — one row
    per function. Returns None (not a partial dict) when there's nothing to
    parse, so the caller can distinguish "zero functions found" (treat as
    failure) from "found functions, all simple" (a real, good score)."""
    rows = []
    for line in (raw or "").splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            continue
        try:
            _nloc, ccn, _token, _param, length = (int(float(p)) for p in parts[:5])
        except ValueError:
            continue
        rows.append({"ccn": ccn, "length": length})
    if not rows:
        return None
    complexities = [r["ccn"] for r in rows]
    lengths = [r["length"] for r in rows]
    return {
        "avg_complexity": round(sum(complexities) / len(complexities), 1),
        "max_complexity": max(complexities),
        "avg_function_length": round(sum(lengths) / len(lengths), 1),
        "longest_function": max(lengths),
        "function_count": len(rows),
    }


def _parse_ruff_json(raw: str) -> Optional[int]:
    try:
        violations = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return len(violations) if isinstance(violations, list) else None


def _score_code_quality(analysis: dict) -> tuple[int, str]:
    """Deterministic code_quality score from a run_static_analysis() result.
    Deduction-based, starts at 100. Java submissions (lint_violation_count is
    None) skip the lint sub-component entirely rather than penalizing for a
    check that was never run — the rationale text says so explicitly, per
    the plan's disclosed-not-hidden principle."""
    if analysis.get("failed"):
        return _FALLBACK_SCORE, f"Static analysis unavailable — {analysis.get('reason', 'unknown error')}."

    score = 100
    notes = []

    avg_complexity = analysis.get("avg_complexity")
    if avg_complexity is not None:
        if avg_complexity > _COMPLEXITY_BAD:
            score -= 30
            notes.append(f"high average cyclomatic complexity ({avg_complexity})")
        elif avg_complexity > _COMPLEXITY_OK:
            score -= 15
            notes.append(f"elevated average cyclomatic complexity ({avg_complexity})")

    lint_count = analysis.get("lint_violation_count")
    function_count = analysis.get("function_count") or 0
    if lint_count is not None and function_count > 0:
        rate = lint_count / function_count
        if rate > _LINT_VIOLATIONS_PER_FUNCTION_BAD:
            score -= 30
            notes.append(f"{lint_count} lint violations across {function_count} functions")
        elif rate > _LINT_VIOLATIONS_PER_FUNCTION_OK:
            score -= 15
            notes.append(f"{lint_count} lint violations across {function_count} functions")
    elif lint_count is None:
        notes.append("lint check unavailable for this language (Python-only)")

    score = max(0, min(100, score))
    rationale = "Static analysis: " + ("; ".join(notes) if notes else "no significant issues found") + "."
    return score, rationale


def _score_architecture(analysis: dict) -> tuple[int, str]:
    """Deterministic architecture score — proxies "reasonable structure" with
    function-length and peak-complexity distribution, since that's what
    lizard can actually see without understanding the problem being solved.
    Coarser than AI judgment by design (see the plan's disclosed
    "fixed thresholds don't know problem difficulty" limitation)."""
    if analysis.get("failed"):
        return _FALLBACK_SCORE, f"Static analysis unavailable — {analysis.get('reason', 'unknown error')}."

    score = 100
    notes = []

    longest = analysis.get("longest_function")
    if longest is not None:
        if longest > _FUNCTION_LENGTH_BAD:
            score -= 30
            notes.append(f"longest function is {longest} lines")
        elif longest > _FUNCTION_LENGTH_OK:
            score -= 15
            notes.append(f"longest function is {longest} lines")

    max_complexity = analysis.get("max_complexity")
    if max_complexity is not None and max_complexity > _COMPLEXITY_BAD:
        score -= 20
        notes.append(f"peak function complexity is {max_complexity}")

    score = max(0, min(100, score))
    rationale = "Static analysis: " + ("; ".join(notes) if notes else "no significant structural issues found") + "."
    return score, rationale
