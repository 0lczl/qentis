"""Reproducibility information; no environment variables or credentials recorded."""

from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import platform
import subprocess

DEPENDENCIES = ("numpy", "scipy", "qutip", "streamlit", "plotly", "scikit-learn")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def dependency_versions() -> dict[str, str]:
    return {name: version(name) for name in DEPENDENCIES}


def capture_provenance() -> dict:
    files = [*PROJECT_ROOT.glob("qentis/*.py"), PROJECT_ROOT / "app.py",
             PROJECT_ROOT / "requirements.txt", PROJECT_ROOT / "requirements.lock",
             PROJECT_ROOT / ".streamlit/config.toml", PROJECT_ROOT / "assets/dashboard.css",
             PROJECT_ROOT / "assets/brand/qentis-logo-reference.png"]
    digests = {str(path.relative_to(PROJECT_ROOT)): sha256(path.read_bytes()).hexdigest()
               for path in sorted(files) if path.is_file()}
    source_digest = sha256("".join(f"{name}:{digest}\n" for name, digest in digests.items()).encode()).hexdigest()
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
                                  text=True, timeout=2, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = None
    return {"python": platform.python_version(), "platform": platform.platform(),
            "dependencies": dependency_versions(), "code_revision": revision,
            "source_digest": source_digest, "source_files_sha256": digests}
