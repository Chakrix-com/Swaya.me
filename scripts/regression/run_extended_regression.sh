#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

print_header "Suite D: Extended Regression (Advisory)"

export BASE_URL="${BASE_URL:-https://test.swaya.me/api/v1}"
export APP_BASE_URL="${APP_BASE_URL:-https://test.swaya.me}"
export SELENIUM_URL="${SELENIUM_URL:-http://localhost:4444/wd/hub}"
export HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
export HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"

FAILED=0

if curl -sS "$SELENIUM_URL/status" >/dev/null 2>&1; then
  run_step "extended_rejoin_simple" "$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/test_rejoin_simple.py" || FAILED=1
  run_step "extended_wordcloud_e2e" "$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/test_word_cloud_e2e.py" || FAILED=1
else
  log_warn "Selenium not reachable at $SELENIUM_URL; skipping Suite D"
fi

if [ "$FAILED" -ne 0 ]; then
  log_error "Suite D failed (advisory)"
  exit 1
fi

log_success "Suite D completed"

