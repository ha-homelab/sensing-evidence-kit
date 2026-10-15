#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
cd "$(dirname "$0")/.."
if [ -z "${EVIDENCE_PYTHON:-}" ]; then
    if [ -x .venv/bin/python3 ]; then
        EVIDENCE_PYTHON=.venv/bin/python3
    else
        EVIDENCE_PYTHON=python3
    fi
fi
PYTHONPATH="$(pwd)/src"
export PYTHONPATH
export PYTHONHASHSEED=0
export PYTHONDONTWRITEBYTECODE=1
"$EVIDENCE_PYTHON" -m ruff check src tests scripts/build_release.py scripts/run_tests.py scripts/validate_repository.py
"$EVIDENCE_PYTHON" -m ruff format --check src tests scripts/build_release.py scripts/run_tests.py scripts/validate_repository.py
"$EVIDENCE_PYTHON" scripts/run_tests.py
"$EVIDENCE_PYTHON" scripts/validate_repository.py
