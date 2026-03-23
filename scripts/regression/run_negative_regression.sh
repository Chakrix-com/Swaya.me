#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

print_header "Suite C: Negative / Abuse Regression"

export BASE_URL="${BASE_URL:-https://test.swaya.me/api/v1}"
export HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
export HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"

FAILED=0

run_step "negative_security_checks" "$ROOT_DIR/backend/.venv/bin/python" "$SCRIPT_DIR/negative_checks.py"                        || FAILED=1
run_step "negative_xss_guard"       "$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/test_rich_text_regression.py" --xss-only || FAILED=1

if [ "$FAILED" -ne 0 ]; then
  log_error "Suite C failed"
  exit 1
fi

log_success "Suite C passed"

