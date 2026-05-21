#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

print_header "Suite C: Negative / Abuse Regression"

export BASE_URL="${BASE_URL:-https://test.swaya.me/api/v1}"
export HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
export HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"
export REGULAR_USER_EMAIL="${REGULAR_USER_EMAIL:-regression-free@swaya.me}"
export REGULAR_USER_PASSWORD="${REGULAR_USER_PASSWORD:-RegTest2026!}"

FAILED=0

run_step "negative_security_checks"  "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/negative_checks.py"                          || FAILED=1
run_step "negative_xss_guard"        "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_rich_text_regression.py" --xss-only      || FAILED=1
run_step "negative_role_boundaries"  "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/negative_role_boundary_checks.py"            || FAILED=1
run_step "negative_tenant_isolation" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_tenant_isolation.py"                    || FAILED=1
run_step "negative_rate_limiting"    "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/test_rate_limiting.py"                              || FAILED=1

if [ "$FAILED" -ne 0 ]; then
  log_error "Suite C failed"
  exit 1
fi

log_success "Suite C passed"

