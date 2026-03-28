#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PATH="$ROOT_DIR/backend/.venv"

# Use virtualenv python
PYTHON_EXE="$VENV_PATH/bin/python"
PYTEST_EXE="$VENV_PATH/bin/pytest"

# Required environment variables
export APP_BASE_URL="${APP_BASE_URL:-https://test.swaya.me}"
export HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
export HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"
export REGULAR_USER_EMAIL="${REGULAR_USER_EMAIL:-regression-free@swaya.me}"
export REGULAR_USER_PASSWORD="${REGULAR_USER_PASSWORD:-RegTest2026!}"

echo "====================================================================="
echo "Suite E: UI Frontend Regression (Playwright)"
echo "Target: $APP_BASE_URL"
echo "====================================================================="

# Run all UI tests headlessly
$PYTEST_EXE "$SCRIPT_DIR/ui/tests/" -s --browser chromium \
  --screenshot only-on-failure --output "$SCRIPT_DIR/reports/ui_artifacts" --tb=short

exit $?
