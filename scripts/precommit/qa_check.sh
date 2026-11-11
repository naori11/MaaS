#!/usr/bin/env bash
# Deterministic QA Pre-commit Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHONIOENCODING=utf-8 python -X utf8 "$SCRIPT_DIR/qa_check.py" "$@"
exit $?
