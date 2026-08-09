"""
Static analysis for hybrid/deterministic grading mode (2026-08-09
grading-mode selector). See static_analysis.py's module docstring and
_private/coding_challenge_grading_mode_plan_20260809.md §2/§7/§8.
"""
from unittest.mock import AsyncMock, patch

import pytest

from features.coding_challenge import static_analysis as sa


# ─── _parse_lizard_csv ──────────────────────────────────────────────────────

def test_parse_lizard_csv_computes_aggregate_metrics():
    # NLOC,CCN,token,PARAM,length,location
    raw = (
        "10,3,50,2,12,foo@1-12@file.py\n"
        "40,15,200,4,45,bar@20-65@file.py\n"
    )
    metrics = sa._parse_lizard_csv(raw)
    assert metrics["function_count"] == 2
    assert metrics["avg_complexity"] == 9.0
    assert metrics["max_complexity"] == 15
    assert metrics["longest_function"] == 45


def test_parse_lizard_csv_returns_none_for_no_functions():
    assert sa._parse_lizard_csv("") is None
    assert sa._parse_lizard_csv("garbage, not, csv\n") is None


# ─── _parse_ruff_json ───────────────────────────────────────────────────────

def test_parse_ruff_json_counts_violations():
    assert sa._parse_ruff_json('[{"code": "E501"}, {"code": "F401"}]') == 2
    assert sa._parse_ruff_json("[]") == 0


def test_parse_ruff_json_returns_none_on_garbage():
    assert sa._parse_ruff_json("not json") is None
    assert sa._parse_ruff_json('{"not": "a list"}') is None


# ─── run_static_analysis: fallback paths (plan §7 gap fix) ─────────────────

@pytest.mark.asyncio
async def test_run_static_analysis_fails_gracefully_on_exec_exception():
    with patch.object(sa.coder_client, "exec_in_workspace", AsyncMock(side_effect=Exception("ssh broken"))):
        result = await sa.run_static_analysis("ws-1", "python")
    assert result["failed"] is True
    assert "ssh broken" in result["reason"]
    assert result["avg_complexity"] is None


@pytest.mark.asyncio
async def test_run_static_analysis_fails_gracefully_on_unparseable_output():
    with patch.object(sa.coder_client, "exec_in_workspace", AsyncMock(return_value=("", "", 0))):
        result = await sa.run_static_analysis("ws-1", "python")
    assert result["failed"] is True


@pytest.mark.asyncio
async def test_run_static_analysis_python_runs_both_tools():
    lizard_csv = "10,3,50,2,12,foo@1-12@file.py\n"
    ruff_json = '[{"code": "E501"}]'
    with patch.object(
        sa.coder_client, "exec_in_workspace",
        AsyncMock(side_effect=[(lizard_csv, "", 0), (ruff_json, "", 0)]),
    ):
        result = await sa.run_static_analysis("ws-1", "python")
    assert result["failed"] is False
    assert result["lint_violation_count"] == 1


@pytest.mark.asyncio
async def test_run_static_analysis_java_skips_ruff():
    lizard_csv = "10,3,50,2,12,foo@1-12@file.py\n"
    with patch.object(
        sa.coder_client, "exec_in_workspace", AsyncMock(return_value=(lizard_csv, "", 0)),
    ) as mock_exec:
        result = await sa.run_static_analysis("ws-1", "java")
    assert result["failed"] is False
    assert result["lint_violation_count"] is None
    assert mock_exec.await_count == 1  # only lizard, never ruff


# ─── _score_code_quality / _score_architecture ─────────────────────────────

def test_score_code_quality_uses_punitive_fallback_on_failure():
    # Gaming-vector fix (8th review pass) — must NOT be a reassuring average.
    score, rationale = sa._score_code_quality({"failed": True, "reason": "timed out"})
    assert score == sa._FALLBACK_SCORE
    assert score < 50
    assert "unavailable" in rationale.lower()


def test_score_code_quality_penalizes_high_complexity():
    clean = {"failed": False, "avg_complexity": 3, "max_complexity": 5,
              "lint_violation_count": 0, "function_count": 10, "longest_function": 20}
    messy = {"failed": False, "avg_complexity": 25, "max_complexity": 30,
              "lint_violation_count": 8, "function_count": 10, "longest_function": 20}
    clean_score, _ = sa._score_code_quality(clean)
    messy_score, _ = sa._score_code_quality(messy)
    assert clean_score == 100
    assert messy_score < clean_score


def test_score_code_quality_skips_lint_subcomponent_for_java():
    analysis = {"failed": False, "avg_complexity": 3, "max_complexity": 5,
                "lint_violation_count": None, "function_count": 10, "longest_function": 20}
    score, rationale = sa._score_code_quality(analysis)
    assert score == 100
    assert "unavailable for this language" in rationale


def test_score_architecture_penalizes_long_functions():
    clean = {"failed": False, "longest_function": 30, "max_complexity": 5}
    sprawling = {"failed": False, "longest_function": 200, "max_complexity": 25}
    clean_score, _ = sa._score_architecture(clean)
    sprawling_score, _ = sa._score_architecture(sprawling)
    assert clean_score == 100
    assert sprawling_score < clean_score


def test_score_architecture_uses_punitive_fallback_on_failure():
    score, _ = sa._score_architecture({"failed": True, "reason": "no source files"})
    assert score == sa._FALLBACK_SCORE
    assert score < 50
