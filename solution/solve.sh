#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Applying reference solution..."

cp "$SCRIPT_DIR/reference/flag_engine.py" /app/flag_engine.py

echo "Reference solution applied."
