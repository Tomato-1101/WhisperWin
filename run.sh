#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -x "./venv/bin/python" ]]; then
  echo "venv が見つかりません: ./venv/bin/python"
  echo "先に: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  exit 1
fi

exec ./venv/bin/python run.py
