#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

print_header "Pre-Production Promotion Gate"

export REGULAR_USER_EMAIL="${REGULAR_USER_EMAIL:-regression-free@swaya.me}"
export REGULAR_USER_PASSWORD="${REGULAR_USER_PASSWORD:-RegTest2026!}"

FAILED=0

run_step "suite_A_smoke"    bash "$SCRIPT_DIR/run_smoke.sh"               || FAILED=1
run_step "suite_B_core"     bash "$SCRIPT_DIR/run_core_regression.sh"     || FAILED=1
run_step "suite_C_negative" bash "$SCRIPT_DIR/run_negative_regression.sh" || FAILED=1
run_step "suite_D_extended" bash "$SCRIPT_DIR/run_extended_regression.sh" || FAILED=1
run_step "suite_E_ui"       bash "$SCRIPT_DIR/run_ui_regression.sh"       || FAILED=1

if [ "$FAILED" -ne 0 ]; then
  log_error "Promotion gate FAILED (mandatory suites did not pass)"
  exit 1
fi

log_success "Promotion gate PASSED (Suites A+B+C+D+E)"
exit 0

