"""Streamlit Community Cloud entry point; local launcher remains app.py."""

import os

# Small GP fits benefit from a single BLAS thread on shared free hosting.
# Set these before importing NumPy/SciPy through the application.
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

from app import main

main()
