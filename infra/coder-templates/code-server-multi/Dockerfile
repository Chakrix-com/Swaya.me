FROM codercom/enterprise-base:ubuntu

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    openjdk-17-jdk \
    maven \
    && pip3 install --no-cache-dir --break-system-packages \
        pytest pytest-json-report \
        ruff lizard \
    && rm -rf /var/lib/apt/lists/*
# ruff/lizard: grading-mode-selector's static analysis (2026-08-09, see
# _private/coding_challenge_grading_mode_plan_20260809.md §2) — lizard is
# language-agnostic (covers Java too, no build required), ruff is Python-only
# lint. Workspaces provisioned from an older template version without these
# binaries fall back gracefully (static_analysis.py's punitive-neutral
# result), so this isn't a hard cutover requirement.

USER coder
