#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
qentis_python="${QENTIS_PYTHON:-python3.11}"
if ! command -v "$qentis_python" >/dev/null 2>&1; then
  echo 'Install Python 3.11, or set QENTIS_PYTHON to its executable path.' >&2
  exit 1
fi
"$qentis_python" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Qentis requires Python 3.11"'
if [ ! -x .venv/bin/python ]; then
  "$qentis_python" -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.lock
.venv/bin/python -c 'from qentis.physics import validate_reference; import streamlit, plotly, sklearn; validate_reference()'
echo 'Setup complete. Launch with ./run.sh and open http://localhost:8501'
