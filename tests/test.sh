#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd /app

echo "Running public tests..."
PYTHONPATH=/app python -m pytest public_tests -q

echo "Running hidden tests..."
PYTHONPATH=/app python -m pytest "$SCRIPT_DIR/hidden/test_hidden.py" -q

echo "All checks passed."
