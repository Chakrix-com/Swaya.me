#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

print_header "Suite B: Core Functional Regression"

export BASE_URL="${BASE_URL:-https://test.swaya.me/api/v1}"
export APP_BASE_URL="${APP_BASE_URL:-https://test.swaya.me}"
export HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
export HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"

FAILED=0

run_step "core_smoke_suite" bash "$SCRIPT_DIR/run_smoke.sh" || FAILED=1
run_step "core_leaderboard_timing" "$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/test_leaderboard_timing.py" || FAILED=1

if [ "$FAILED" -ne 0 ]; then
  log_error "Suite B failed"
  exit 1
fi

log_success "Suite B passed"

