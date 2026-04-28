#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

print_header "Suite B: Core Functional Regression"

export BASE_URL="${BASE_URL:-https://test.swaya.me/api/v1}"
export APP_BASE_URL="${APP_BASE_URL:-https://test.swaya.me}"
export HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
export HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"
export REGULAR_USER_EMAIL="${REGULAR_USER_EMAIL:-regression-free@swaya.me}"
export REGULAR_USER_PASSWORD="${REGULAR_USER_PASSWORD:-RegTest2026!}"

FAILED=0

run_step "core_smoke_suite"        bash "$SCRIPT_DIR/run_smoke.sh"                                                                       || FAILED=1
run_step "core_smoke_routes"       bash "$SCRIPT_DIR/smoke_routes.sh"                                                                    || FAILED=1
run_step "core_leaderboard_timing" "$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/test_leaderboard_timing.py"                           || FAILED=1
run_step "core_regular_user_flows" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_regular_user_flows.py"                         || FAILED=1
run_step "core_folders_templates"  "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_folders_templates.py"                          || FAILED=1
run_step "core_offline_poll"       "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_offline_poll_lifecycle.py"                     || FAILED=1
run_step "core_exam_lifecycle"     "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_exam_lifecycle.py"                             || FAILED=1
run_step "core_quiz_type_persistence" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_quiz_type_persistence.py"      || FAILED=1
run_step "core_admin_api"          "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_admin_api_coverage.py"                         || FAILED=1
run_step "core_misc_endpoints"     "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_misc_endpoints.py"                             || FAILED=1
run_step "core_text_question_types" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_text_question_types.py"                       || FAILED=1
run_step "core_live_poll"          "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_live_poll_lifecycle.py"                        || FAILED=1
run_step "core_question_reorder"   "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_question_reorder.py"                           || FAILED=1
run_step "core_anonymous_participant" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_anonymous_participant.py"                   || FAILED=1
run_step "core_question_features"  "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_question_features.py"                          || FAILED=1
run_step "core_proctoring"         "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_proctoring.py"                                   || FAILED=1
run_step "core_oauth_welcome_email" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_oauth_welcome_email.py"                          || FAILED=1
run_step "core_quiz_import_export" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_quiz_import_export.py"                            || FAILED=1
run_step "core_uploads"            "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_uploads.py"                                       || FAILED=1
run_step "core_password_reset"     "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_password_reset_flow.py"                           || FAILED=1

if [ "$FAILED" -ne 0 ]; then
  log_error "Suite B failed"
  exit 1
fi

log_success "Suite B passed"

