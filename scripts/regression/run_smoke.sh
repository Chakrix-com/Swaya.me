#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

print_header "Suite A: Release Smoke"

export BASE_URL="${BASE_URL:-https://test.swaya.me/api/v1}"
export HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
export HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"

FAILED=0

run_step "smoke_api_flow" bash "$ROOT_DIR/test_api_flow.sh" || FAILED=1
run_step "smoke_session_lifecycle" "$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/test_session_lifecycle.py" || FAILED=1

if [ "$FAILED" -ne 0 ]; then
  log_error "Suite A failed"
  exit 1
fi

log_success "Suite A passed"

