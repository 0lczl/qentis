#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ ! -x .venv/bin/python ]; then
  echo 'Set up Qentis first: ./setup.sh' >&2
  exit 1
fi
exec .venv/bin/python -m streamlit run app.py --server.address=127.0.0.1 "$@"
