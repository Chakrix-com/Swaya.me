#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="${REPORT_DIR:-$ROOT_DIR/scripts/regression/reports}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$REPORT_DIR"

COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_NC='\033[0m'

log_info() {
  echo -e "${COLOR_BLUE}[INFO]${COLOR_NC} $*"
}

log_warn() {
  echo -e "${COLOR_YELLOW}[WARN]${COLOR_NC} $*"
}

log_error() {
  echo -e "${COLOR_RED}[ERROR]${COLOR_NC} $*"
}

log_success() {
  echo -e "${COLOR_GREEN}[PASS]${COLOR_NC} $*"
}

run_step() {
  local name="$1"
  shift
  local logfile="$REPORT_DIR/${RUN_ID}_${name}.log"
  log_info "Running: $name"
  if "$@" >"$logfile" 2>&1; then
    log_success "$name"
    return 0
  fi
  log_error "$name (see $logfile)"
  return 1
}

print_header() {
  echo
  echo "====================================================================="
  echo "$*"
  echo "====================================================================="
}

