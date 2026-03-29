#!/bin/bash
# =============================================================================
# run_tests.sh — Swaya.me Regression Test Runner
# =============================================================================
# Runs the full test suite (or selected suites) against test.swaya.me.
#
# Usage:
#   ./run_tests.sh [OPTIONS]
#
# Options:
#   -s, --suite SUITE     Run only this suite: smoke|core|negative|extended|ui|all
#                         Default: all
#   -u, --api-url URL     API base URL  (default: https://test.swaya.me/api/v1)
#   -a, --app-url URL     App base URL  (default: https://test.swaya.me)
#       --admin-email E   Admin user email   (default: demo@swaya.me)
#       --admin-pass  P   Admin user password
#       --user-email  E   Regular user email (default: regression-free@swaya.me)
#       --user-pass   P   Regular user password
#   -v, --verbose         Stream full step output to terminal (not just summary)
#   -h, --help            Show this help
#
# Environment variable equivalents (override defaults):
#   BASE_URL, APP_BASE_URL, HOST_EMAIL, HOST_PASSWORD,
#   REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD
#
# Examples:
#   ./run_tests.sh                                # full gate (all suites)
#   ./run_tests.sh -s smoke                       # smoke only
#   ./run_tests.sh -s core -v                     # core with live output
#   ./run_tests.sh -s extended                    # Selenium E2E (needs container)
#   ./run_tests.sh -s ui                          # Playwright UI
#   ./run_tests.sh --api-url https://test.swaya.me/api/v1 -s all
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGRESSION_DIR="$SCRIPT_DIR/scripts/regression"
REPORT_DIR="$REGRESSION_DIR/reports"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
export RUN_ID REPORT_DIR
mkdir -p "$REPORT_DIR"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Defaults ──────────────────────────────────────────────────────────────────
SUITE="all"
VERBOSE=0

# ── Parse arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--suite)        SUITE="$2";                    shift 2 ;;
    -u|--api-url)      export BASE_URL="$2";          shift 2 ;;
    -a|--app-url)      export APP_BASE_URL="$2";      shift 2 ;;
    --admin-email)     export HOST_EMAIL="$2";        shift 2 ;;
    --admin-pass)      export HOST_PASSWORD="$2";     shift 2 ;;
    --user-email)      export REGULAR_USER_EMAIL="$2";  shift 2 ;;
    --user-pass)       export REGULAR_USER_PASSWORD="$2"; shift 2 ;;
    -v|--verbose)      VERBOSE=1;                     shift   ;;
    -h|--help)
      cat <<'HELP'
run_tests.sh — Swaya.me Regression Test Runner

USAGE
  ./run_tests.sh [OPTIONS]

OPTIONS
  -s, --suite SUITE     Suite to run: smoke | core | negative | extended | ui | all
                        Default: all
  -u, --api-url URL     API base URL        (default: https://test.swaya.me/api/v1)
  -a, --app-url URL     App base URL        (default: https://test.swaya.me)
      --admin-email E   Admin email         (default: demo@swaya.me)
      --admin-pass  P   Admin password
      --user-email  E   Regular user email  (default: regression-free@swaya.me)
      --user-pass   P   Regular user password
  -v, --verbose         Stream full step output to terminal (not just summary)
  -h, --help            Show this help

SUITES
  smoke     (A) ~11s  — API health, session lifecycle, regular user login
  core      (B) ~50s  — Full API coverage: quiz CRUD, sessions, answers, admin
  negative  (C) ~18s  — 401/403 role boundary + tenant isolation checks
  extended  (D) ~90s  — Selenium E2E: rejoin flow, word cloud  (needs selenium-arm)
  ui        (E) ~90s  — Playwright: quiz builder, audience flow, dashboard, auth pages

EXAMPLES
  ./run_tests.sh                          # full gate — all 5 suites (~4 min)
  ./run_tests.sh -s smoke                 # smoke only
  ./run_tests.sh -s core -v              # core with live output
  ./run_tests.sh -s extended             # Selenium E2E (selenium-arm must be running)
  ./run_tests.sh -s ui                   # Playwright UI tests
  ./run_tests.sh --admin-email me@x.com --admin-pass secret -s all

ENV VARS (alternative to flags)
  BASE_URL  APP_BASE_URL  SELENIUM_URL
  HOST_EMAIL  HOST_PASSWORD
  REGULAR_USER_EMAIL  REGULAR_USER_PASSWORD

REPORTS
  All logs written to: scripts/regression/reports/<RUN_ID>_<suite>.log
HELP
      exit 0 ;;
    *) echo "Unknown option: $1  (use -h for help)"; exit 1 ;;
  esac
done

# ── Env export with defaults ──────────────────────────────────────────────────
export BASE_URL="${BASE_URL:-https://test.swaya.me/api/v1}"
export APP_BASE_URL="${APP_BASE_URL:-https://test.swaya.me}"
export SELENIUM_URL="${SELENIUM_URL:-http://localhost:4444/wd/hub}"
export HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
export HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"
export REGULAR_USER_EMAIL="${REGULAR_USER_EMAIL:-regression-free@swaya.me}"
export REGULAR_USER_PASSWORD="${REGULAR_USER_PASSWORD:-RegTest2026!}"

# ── Helpers ───────────────────────────────────────────────────────────────────
PASS_COUNT=0
FAIL_COUNT=0
declare -a FAILED_SUITES=()

ts() { date '+%H:%M:%S'; }

run_suite() {
  local label="$1"
  local script="$2"

  echo
  echo -e "${CYAN}${BOLD}━━━ $(ts) ▶  ${label} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

  local safe_label="${label//[: \/]/_}"
  local logfile="$REPORT_DIR/${RUN_ID}_${safe_label}.log"

  if [[ "$VERBOSE" -eq 1 ]]; then
    if bash "$script" 2>&1 | tee "$logfile"; then
      echo -e "${GREEN}${BOLD}✔  ${label} PASSED${NC}"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo -e "${RED}${BOLD}✘  ${label} FAILED${NC}  →  $logfile"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      FAILED_SUITES+=("$label")
    fi
  else
    if bash "$script" >"$logfile" 2>&1; then
      echo -e "${GREEN}${BOLD}✔  ${label} PASSED${NC}  (log: $logfile)"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo -e "${RED}${BOLD}✘  ${label} FAILED${NC}  →  tail of log:"
      tail -30 "$logfile" | sed 's/^/    /'
      echo -e "    ${YELLOW}Full log: $logfile${NC}"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      FAILED_SUITES+=("$label")
    fi
  fi
}

# ── Header ────────────────────────────────────────────────────────────────────
echo
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║          Swaya.me Regression Suite  —  run_tests.sh         ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "  Target   : ${CYAN}${APP_BASE_URL}${NC}"
echo -e "  API      : ${CYAN}${BASE_URL}${NC}"
echo -e "  Admin    : ${HOST_EMAIL}"
echo -e "  RegUser  : ${REGULAR_USER_EMAIL}"
echo -e "  Suite(s) : ${BOLD}${SUITE}${NC}"
echo -e "  Run ID   : ${RUN_ID}"
echo -e "  Reports  : ${REPORT_DIR}/"
echo

# ── Suite selection ───────────────────────────────────────────────────────────
case "$SUITE" in
  smoke)    SUITES=("A:Smoke") ;;
  core)     SUITES=("B:Core") ;;
  negative) SUITES=("C:Negative") ;;
  extended) SUITES=("D:Extended") ;;
  ui)       SUITES=("E:UI") ;;
  all)      SUITES=("A:Smoke" "B:Core" "C:Negative" "D:Extended" "E:UI") ;;
  *)
    echo -e "${RED}Unknown suite '$SUITE'. Choose: smoke core negative extended ui all${NC}"
    exit 1 ;;
esac

START_TIME=$(date +%s)

# ── Run selected suites ───────────────────────────────────────────────────────
for entry in "${SUITES[@]}"; do
  key="${entry%%:*}"
  name="${entry#*:}"
  case "$key" in
    A) run_suite "Suite A: Smoke"             "$REGRESSION_DIR/run_smoke.sh" ;;
    B) run_suite "Suite B: Core API"          "$REGRESSION_DIR/run_core_regression.sh" ;;
    C) run_suite "Suite C: Negative/Security" "$REGRESSION_DIR/run_negative_regression.sh" ;;
    D) run_suite "Suite D: Extended Selenium" "$REGRESSION_DIR/run_extended_regression.sh" ;;
    E) run_suite "Suite E: Playwright UI"     "$REGRESSION_DIR/run_ui_regression.sh" ;;
  esac
done

# ── Summary ───────────────────────────────────────────────────────────────────
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINS=$((ELAPSED / 60))
SECS=$((ELAPSED % 60))

echo
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  SUMMARY  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Elapsed : ${MINS}m ${SECS}s"
echo -e "  Passed  : ${GREEN}${BOLD}${PASS_COUNT}${NC}"
echo -e "  Failed  : ${RED}${BOLD}${FAIL_COUNT}${NC}"

if [[ ${#FAILED_SUITES[@]} -gt 0 ]]; then
  echo
  echo -e "  ${RED}Failed suites:${NC}"
  for s in "${FAILED_SUITES[@]}"; do
    echo -e "    ${RED}✘${NC} $s"
  done
  echo
  echo -e "  ${YELLOW}Logs are in: ${REPORT_DIR}/${NC}"
  echo -e "  ${YELLOW}Tip: re-run a single suite with  ./run_tests.sh -s <name> -v${NC}"
  echo
  exit 1
fi

echo
echo -e "  ${GREEN}${BOLD}ALL SUITES PASSED${NC}"
echo
exit 0
