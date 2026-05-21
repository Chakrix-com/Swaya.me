#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

print_header "Suite D: Extended Regression"

export BASE_URL="${BASE_URL:-https://test.swaya.me/api/v1}"
export APP_BASE_URL="${APP_BASE_URL:-https://test.swaya.me}"
export SELENIUM_URL="${SELENIUM_URL:-http://localhost:4444/wd/hub}"
export HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
export HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"
export REGULAR_USER_EMAIL="${REGULAR_USER_EMAIL:-regression-free@swaya.me}"
export REGULAR_USER_PASSWORD="${REGULAR_USER_PASSWORD:-RegTest2026!}"

FAILED=0

if ! curl -sS "$SELENIUM_URL/status" >/dev/null 2>&1; then
  log_error "Selenium not reachable at $SELENIUM_URL — Suite D cannot run (is selenium-arm container running?)"
  exit 1
fi

# Ensure regular user has required test fixtures (READY quiz with word_cloud question)
run_step "extended_setup_fixtures" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/setup_test_fixtures.py" || FAILED=1

run_step "extended_rejoin_simple"       "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_rejoin_simple.py"                                                                || FAILED=1
run_step "extended_rejoin_regular_user" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_rejoin_simple.py" --user-email "$REGULAR_USER_EMAIL" --user-password "$REGULAR_USER_PASSWORD" || FAILED=1
run_step "extended_wordcloud_e2e"       "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_word_cloud_e2e.py"                                                               || FAILED=1
run_step "extended_wordcloud_regular"   "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_word_cloud_e2e.py" --user-email "$REGULAR_USER_EMAIL" --user-password "$REGULAR_USER_PASSWORD" || FAILED=1
run_step "extended_offline_poll_e2e"    "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_offline_poll_e2e.py"                                                             || FAILED=1
run_step "extended_exam_e2e"            "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_exam_e2e.py"                                                                     || FAILED=1
run_step "extended_proctoring_e2e"      "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_proctoring_e2e.py"                                                               || FAILED=1
run_step "extended_ai_features"         "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_ai_features.py"                                                                  || FAILED=1
run_step "extended_rich_text_e2e"       "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_rich_text_regression.py"                                                         || FAILED=1
run_step "extended_dark_mode"           "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_dark_mode_regression.py"                                                         || FAILED=1

if [ "$FAILED" -ne 0 ]; then
  log_error "Suite D failed"
  exit 1
fi

log_success "Suite D passed"

