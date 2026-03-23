#!/bin/bash
# smoke_routes.sh — Quick curl checks for new public endpoints
# Returns 0 if all routes respond with non-5xx; 1 otherwise

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

APP_BASE_URL="${APP_BASE_URL:-https://test.swaya.me}"
API_BASE="${APP_BASE_URL}/api/v1"
FAILED=0

check_route() {
    local name="$1"
    local url="$2"
    local http_code
    http_code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 10 "$url" || echo "000")
    if [[ "$http_code" == "5"* ]] || [[ "$http_code" == "000" ]]; then
        log_error "smoke_route $name — got $http_code for $url"
        FAILED=1
    else
        log_success "smoke_route $name — $http_code"
    fi
}

print_header "Smoke Routes: New Public Endpoints"

# Offline poll info endpoint (expect 200 or 404, never 500)
check_route "offline_poll_info"   "$API_BASE/offline-poll/smoke-test-slug"

# Exam/Test info endpoint (expect 200 or 404, never 500)
check_route "exam_info"           "$API_BASE/e/smoke-test-slug"

# OG metadata endpoint for join code (expect 200 or 404)
check_route "og_join_metadata"    "$API_BASE/og/join/0000"

# Main app pages — should all return 200
check_route "app_root"            "$APP_BASE_URL/"
check_route "app_login"           "$APP_BASE_URL/login"

if [ "$FAILED" -ne 0 ]; then
    log_error "smoke_routes: one or more routes returned 5xx"
    exit 1
fi

log_success "smoke_routes: all routes OK"
