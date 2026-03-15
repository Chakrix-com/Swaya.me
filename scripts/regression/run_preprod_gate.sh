#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

print_header "Pre-Production Promotion Gate"

RUN_EXTENDED="${RUN_EXTENDED:-0}"

FAILED=0

run_step "suite_A_smoke" bash "$SCRIPT_DIR/run_smoke.sh" || FAILED=1
run_step "suite_B_core" bash "$SCRIPT_DIR/run_core_regression.sh" || FAILED=1
run_step "suite_C_negative" bash "$SCRIPT_DIR/run_negative_regression.sh" || FAILED=1

if [ "$RUN_EXTENDED" = "1" ]; then
  run_step "suite_D_extended" bash "$SCRIPT_DIR/run_extended_regression.sh" || log_warn "Suite D failed (advisory)"
else
  log_info "Suite D skipped (set RUN_EXTENDED=1 to enable)"
fi

if [ "$FAILED" -ne 0 ]; then
  log_error "Promotion gate FAILED (mandatory suites did not pass)"
  exit 1
fi

log_success "Promotion gate PASSED (Suites A+B+C)"
exit 0

