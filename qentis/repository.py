"""Versioned, non-executable numerical artifacts committed atomically on disk."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import shutil
from uuid import uuid4
import zipfile

import numpy as np

from .config import ExperimentConfig, PHYSICAL_CONVENTION, SolverSettings
from .experiment import Run, SCHEMA_VERSION
from .physics import Trajectory, require_valid
from .provenance import dependency_versions

MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
RUN_ID_PATTERN = re.compile(r"qentis-[0-9a-f]{32}\Z")


class RepositoryError(RuntimeError):
    """A local run could not be saved or opened; existing files are preserved."""


class IntegrityError(RepositoryError):
    """An artifact is missing, corrupt, or inconsistent."""


class CompatibilityError(RepositoryError):
    """A saved schema or environment is not supported."""


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    created_at: str | None
    configuration: dict | None
    error: str | None = None


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _read(path: Path) -> bytes:
    if path.is_symlink():
        raise IntegrityError(f"Symbolic-link artifact is unsupported: {path.name}.")
    if not path.is_file():
        raise IntegrityError(f"Missing artifact: {path.name}. Restore the original run directory.")
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise IntegrityError(f"Artifact is too large: {path.name}.")
    return path.read_bytes()


class RunRepository:
    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()

    def list_runs(self) -> list[RunSummary]:
        if not self.root.exists():
            return []
        try:
            summaries = []
            for path in self.root.iterdir():
                if not RUN_ID_PATTERN.fullmatch(path.name) or not path.is_dir() or path.is_symlink():
                    continue
                try:
                    metadata = self._metadata(path)
                    summaries.append(RunSummary(path.name, metadata["created_at"], metadata["configuration"]))
                except RepositoryError as exc:
                    summaries.append(RunSummary(path.name, None, None, str(exc)))
            return sorted(summaries, key=lambda item: (item.created_at or "", item.run_id), reverse=True)
        except OSError as exc:
            raise RepositoryError(f"Cannot read the results folder: {exc}") from exc

    def save(self, run: Run) -> None:
        """Commit a new immutable result; a failed/partial write is never listed."""
        if not RUN_ID_PATTERN.fullmatch(run.run_id):
            raise RepositoryError("Invalid run identifier.")
        require_valid(run.trajectory)
        self._validate_metadata(run.metadata)
        staging = self.root / f".pending-{uuid4().hex}"
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            if (self.root / run.run_id).exists():
                raise RepositoryError("This run already exists. Run a new simulation to create another result.")
            staging.mkdir()
            data = io.BytesIO()
            np.savez_compressed(data, times=run.trajectory.times, states=run.trajectory.states)
            artifacts = {"run.json": _json_bytes(run.metadata), "trajectory.npz": data.getvalue()}
            for name, content in artifacts.items():
                with (staging / name).open("xb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
            manifest = {"schema_version": SCHEMA_VERSION, "algorithm": "sha256", "artifacts": {
                name: {"sha256": sha256(content).hexdigest(), "bytes": len(content)}
                for name, content in artifacts.items()}}
            with (staging / "manifest.json").open("xb") as handle:
                handle.write(_json_bytes(manifest))
                handle.flush()
                os.fsync(handle.fileno())
            descriptor = os.open(staging, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.replace(staging, self.root / run.run_id)
            descriptor = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise RepositoryError(f"The result was not confirmed saved: {exc}. Check disk space and folder permissions.") from exc
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    def load(self, run_id: str) -> Run:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise RepositoryError("Invalid run identifier. Choose a run from Saved runs.")
        path = self.root / run_id
        if path.is_symlink():
            raise IntegrityError("Symbolic-link run directories are unsupported.")
        try:
            metadata = self._metadata(path)
            if metadata.get("kind") == "qubit-learning":
                from .learning_storage import load_learning
                return load_learning(path)
            raw = _read(path / "trajectory.npz")
            self._verify(path, "trajectory.npz", raw)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if (set(archive.namelist()) != {"times.npy", "states.npy"}
                        or sum(item.file_size for item in archive.infolist()) > MAX_ARTIFACT_BYTES):
                    raise IntegrityError("The numerical artifact has an unsupported layout or size.")
            with np.load(io.BytesIO(raw), allow_pickle=False) as data:
                config = ExperimentConfig(**metadata["configuration"])
                trajectory = Trajectory(config.gamma, data["times"], data["states"],
                                        tuple(metadata["numerical_warnings"]))
            if (trajectory.times.shape != (config.time_samples,)
                    or not np.array_equal(trajectory.times, np.linspace(0, config.max_time, config.time_samples))):
                raise IntegrityError("Stored trajectory times do not match the immutable configuration.")
            report = require_valid(trajectory)
            if report.to_dict() != metadata["trajectory_validation"]:
                raise IntegrityError("Stored validation diagnostics do not match the numerical result.")
            return Run(metadata, trajectory)
        except RepositoryError:
            raise
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError) as exc:
            raise IntegrityError(f"Cannot open this numerical result: {exc}. Original files were preserved.") from exc

    def _verify(self, path: Path, name: str, content: bytes) -> None:
        manifest = json.loads(_read(path / "manifest.json"))
        if not isinstance(manifest, dict):
            raise IntegrityError("The integrity manifest must be a JSON object.")
        if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != SCHEMA_VERSION:
            raise CompatibilityError("Unsupported manifest schema. Open this result with its original application version.")
        if manifest.get("algorithm") != "sha256" or set(manifest.get("artifacts", {})) != {"run.json", "trajectory.npz"}:
            raise IntegrityError("The integrity manifest has an unsupported format.")
        expected = manifest["artifacts"][name]
        if expected != {"sha256": sha256(content).hexdigest(), "bytes": len(content)}:
            raise IntegrityError(f"Checksum mismatch: {name}. Restore the original artifact; no result was loaded.")

    def _metadata(self, path: Path) -> dict:
        try:
            raw = _read(path / "run.json")
            manifest = json.loads(_read(path / "manifest.json"))
            if not isinstance(manifest, dict):
                raise IntegrityError("The integrity manifest must be a JSON object.")
            if manifest.get("schema_version") in (2, 3):
                from .learning_storage import learning_metadata
                return learning_metadata(path)
            self._verify(path, "run.json", raw)
            metadata = json.loads(raw)
            self._validate_metadata(metadata)
            if metadata["run_id"] != path.name:
                raise IntegrityError("Run identifier does not match its directory.")
            return metadata
        except RepositoryError:
            raise
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise IntegrityError(f"Invalid run metadata: {exc}.") from exc

    @staticmethod
    def _validate_metadata(metadata: dict) -> None:
        if not isinstance(metadata, dict):
            raise IntegrityError("Run metadata must be a JSON object.")
        if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != SCHEMA_VERSION:
            raise CompatibilityError("Unsupported run schema. Open this result with its original application version.")
        if metadata.get("kind") != "qubit-simulation" or metadata.get("status") != "complete":
            raise CompatibilityError("This application can open completed phase-one qubit simulations only.")
        ExperimentConfig(**metadata["configuration"])
        SolverSettings(**metadata["solver"]["settings"])
        if not isinstance(metadata.get("run_id"), str) or not RUN_ID_PATTERN.fullmatch(metadata["run_id"]):
            raise IntegrityError("Invalid stored run identifier.")
        if metadata["solver"].get("library") != "qutip" or metadata["solver"].get("function") != "mesolve":
            raise CompatibilityError("The saved numerical solver is unsupported.")
        for key in ("created_at", "completed_at"):
            if not isinstance(metadata.get(key), str) or datetime.fromisoformat(metadata[key]).utcoffset() is None:
                raise IntegrityError(f"Invalid timestamp: {key}.")
        if metadata["physical_convention"] != PHYSICAL_CONVENTION:
            raise CompatibilityError("The saved physical convention differs from this application.")
        if not metadata["reference_validation"]["passed"] or not metadata["trajectory_validation"]["passed"]:
            raise IntegrityError("The stored numerical reference did not pass validation.")
        if metadata["provenance"]["dependencies"] != dependency_versions():
            raise CompatibilityError("Dependency versions differ. Restore the recorded pinned environment before opening this run.")
        for key in ("created_at", "completed_at", "counts", "numerical_warnings", "timing"):
            if key not in metadata:
                raise IntegrityError(f"Missing run metadata: {key}.")

    def save_checkpoint(self, run) -> None:
        if not RUN_ID_PATTERN.fullmatch(run.run_id):
            raise RepositoryError("Invalid learning run identifier.")
        from .learning_storage import save_checkpoint
        save_checkpoint(self.root, run)

    def record_failure(self, run) -> None:
        from .learning_storage import record_failure
        record_failure(self.root, run)

    def begin_learning(self, run) -> None:
        if not RUN_ID_PATTERN.fullmatch(run.run_id):
            raise RepositoryError("Invalid learning run identifier.")
        from .learning_storage import begin_learning
        begin_learning(self.root, run)

    def save_status(self, run, status: str) -> None:
        from .learning_storage import save_status
        save_status(self.root, run, status)
