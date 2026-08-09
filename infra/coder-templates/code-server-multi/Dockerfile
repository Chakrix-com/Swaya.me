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

# Pre-install code-server into the image (2026-08-09) — fixes a recurring 502
# on every workspace (re)start, not just first creation. Root cause: this
# template's docker_container resource has count = start_count, so stopping a
# workspace fully destroys the container and starting it recreates one from
# scratch — only /home/coder survives, via its own separate docker_volume.
# code-server itself was never part of that: the registry `code-server`
# module installs it at container *startup* by downloading a fresh tarball
# from GitHub to /tmp/code-server, which takes a few minutes on this ARM box
# — any request during that window 502s because nothing is listening yet.
# And restarts aren't rare: run_grading_job's stop_workspace()/start_workspace()
# cycle means this replays on every single grading run, not just once.
#
# The module's own install script (registry.coder.com/coder/code-server/coder)
# already checks `[ ! -f /tmp/code-server/bin/code-server ]` before
# downloading anything — baking the binary into the image at this exact path
# makes every fresh container start with it already present, so the module
# just launches the process instead of installing it first. Version pinned to
# match what was already being downloaded live in this environment
# (confirmed via `coder ssh` into a running workspace mid-install).
RUN curl -fsSL https://code-server.dev/install.sh | sh -s -- \
        --method=standalone --prefix=/tmp/code-server --version=4.131.0 \
    && chown -R coder:coder /tmp/code-server

USER coder
