"""Atomic immutable learning revisions; JSON models never execute serialized code."""

from dataclasses import asdict
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
from uuid import uuid4

import numpy as np

from .config import LearningConfig, PHYSICAL_CONVENTION, SolverSettings
from .evaluation import EvaluationSet, evaluate
from .learning import (IterationCheckpoint, LearningRun, Observation, STRATEGIES,
                       StrategyState, candidate_pool)
from .physics import Trajectory, require_valid
from .provenance import dependency_versions
from .repository import CompatibilityError, IntegrityError, RepositoryError, _json_bytes, _read
from .surrogate import FIT_POLICY, SurrogateModel


def _sync(folder: Path) -> None:
    descriptor = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _commit_directory(destination: Path, artifacts: dict[str, bytes], schema=2) -> None:
    staging = destination.parent / f".pending-{uuid4().hex}"
    try:
        staging.mkdir()
        for name, raw in artifacts.items():
            _write(staging / name, raw)
        _write(staging / "manifest.json", _json_bytes({"schema_version": schema, "algorithm": "sha256", "artifacts": {
            name: {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)} for name, raw in artifacts.items()}}))
        _sync(staging)
        if destination.exists():
            # Retry after an unconfirmed directory rename never overwrites a revision.
            for name, raw in artifacts.items():
                if _verified(destination, name) != raw:
                    raise IntegrityError("An immutable learning revision already exists with different content.")
        else:
            os.replace(staging, destination)
            _sync(destination.parent)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def _verified(path: Path, name: str) -> bytes:
    raw = _read(path / name)
    manifest = json.loads(_read(path / "manifest.json"))
    if not isinstance(manifest, dict):
        raise IntegrityError("The learning integrity manifest must be a JSON object.")
    if manifest.get("schema_version") not in (2, 3) or manifest.get("algorithm") != "sha256":
        raise CompatibilityError("Unsupported learning manifest schema.")
    if manifest.get("artifacts", {}).get(name) != {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}:
        raise IntegrityError(f"Checksum mismatch: {name}.")
    return raw


def learning_metadata(path: Path) -> dict:
    data = json.loads(_verified(path, "run.json"))
    if not isinstance(data, dict):
        raise IntegrityError("Learning run metadata must be a JSON object.")
    if data.get("schema_version") not in (2, 3) or data.get("kind") != "qubit-learning":
        raise CompatibilityError("Unsupported learning run schema.")
    LearningConfig(**data["configuration"])
    SolverSettings(**data["solver"])
    if data["run_id"] != path.name or data["physical_convention"] != PHYSICAL_CONVENTION:
        raise IntegrityError("Learning run identity or physical convention does not match.")
    if data["fit_policy"] != FIT_POLICY or data["provenance"]["dependencies"] != dependency_versions():
        raise CompatibilityError("Restore the recorded pinned environment/model policy before opening this learning run.")
    if data["schema_version"] == 2 and not data["reference_validation"]["passed"]:
        raise IntegrityError("The learning reference did not pass validation.")
    return data


def begin_learning(root: Path, run: LearningRun) -> None:
    """Persist immutable settings before reference preparation starts."""
    try:
        root.mkdir(parents=True, exist_ok=True)
        path = root / run.run_id
        if path.exists():
            raise RepositoryError("This run already exists. Start a new comparison for changed settings.")
        _commit_directory(path, {"run.json": _json_bytes(run.metadata)}, schema=3)
        save_status(root, run, "preparing")
    except OSError as exc:
        raise RepositoryError(f"Learning run was not confirmed saved: {exc}.") from exc


def save_status(root: Path, run: LearningRun, status: str) -> None:
    """Atomic lifecycle/pointer update; never advances an unfinished pair."""
    if status not in {"preparing", "running", "paused", "complete", "failed"}:
        raise RepositoryError("Unsupported learning status.")
    path = root / run.run_id
    temporary = path / f".latest-{uuid4().hex}"
    try:
        pointer = {"schema_version": 3 if run.metadata["schema_version"] == 3 else 2,
                   "iteration": run.latest.iteration if run.checkpoints else -1, "status": status}
        if status == "failed":
            pointer["failure"] = run.metadata.get("failure")
        _write(temporary, _json_bytes(pointer))
        os.replace(temporary, path / "latest.json")
        _sync(path)
    except OSError as exc:
        raise RepositoryError(f"Learning status was not confirmed saved: {exc}.") from exc
    finally:
        temporary.unlink(missing_ok=True)


def save_checkpoint(root: Path, run: LearningRun) -> None:
    path = root / run.run_id
    checkpoint = run.latest
    try:
        root.mkdir(parents=True, exist_ok=True)
        if run.metadata["schema_version"] == 3:
            if not path.exists():
                begin_learning(root, run)
            base = learning_metadata(path)
            if base["configuration"] != run.config.to_dict():
                raise IntegrityError("A checkpoint cannot change historical configuration.")
            prepared = path / "prepared"
            if not prepared.exists():
                buffer = io.BytesIO()
                np.savez_compressed(buffer, times=run.trajectory.times,
                                    states=np.stack([item.states for item in run.visualization_slices]))
                _commit_directory(prepared, {"evaluation.json": _json_bytes(run.evaluation.to_dict()),
                    "trajectory.npz": buffer.getvalue(), "reference.json": _json_bytes({
                        "evaluation_identity": run.evaluation.identity,
                        "reference_validation": run.metadata["reference_validation"]})})
            elif json.loads(_verified(prepared, "reference.json"))["evaluation_identity"] != run.evaluation.identity:
                raise IntegrityError("A checkpoint cannot change evaluation identity.")
        elif not path.exists():
            buffer = io.BytesIO()
            np.savez_compressed(buffer, times=run.trajectory.times,
                                states=np.stack([item.states for item in run.visualization_slices]))
            base = {**run.metadata, "status": "created"}
            _commit_directory(path, {"run.json": _json_bytes(base), "evaluation.json": _json_bytes(run.evaluation.to_dict()),
                                     "trajectory.npz": buffer.getvalue()})
        else:
            base = learning_metadata(path)
            if base["configuration"] != run.config.to_dict() or base["evaluation_identity"] != run.evaluation.identity:
                raise IntegrityError("A checkpoint cannot change historical configuration or evaluation identity.")
        record = {"iteration": checkpoint.iteration, "counts": checkpoint.counts,
                  "elapsed_seconds": checkpoint.elapsed_seconds, "random_state": checkpoint.random_state,
                  "created_at": checkpoint.created_at, "strategies": {}}
        artifacts = {}
        for name in STRATEGIES:
            state = checkpoint.strategies[name]
            artifacts[f"{name}-model.json"] = _json_bytes(state.model.to_dict())
            record["strategies"][name] = {
                "observations": [asdict(item) for item in state.observations], "metrics": state.metrics,
                "selection": state.selection, "next_selection": state.next_selection,
                **{key: getattr(state, key).tolist() for key in
                   ("candidate_mean", "candidate_std", "evaluation_mean", "evaluation_std")}}
        artifacts["checkpoint.json"] = _json_bytes(record)
        revision = path / f"iteration-{checkpoint.iteration:03d}"
        if revision.exists():
            # A crash can leave a fully written revision beyond the confirmed pointer.
            # Preserve that unconfirmed artifact, then write the deterministic retry.
            pointer = json.loads(_read(path / "latest.json"))
            if pointer["iteration"] < checkpoint.iteration:
                os.replace(revision, path / f".unconfirmed-{revision.name}-{uuid4().hex}")
                _sync(path)
        _commit_directory(revision, artifacts)
        save_status(root, run, run.metadata["status"])
    except OSError as exc:
        raise RepositoryError(f"Learning checkpoint was not confirmed saved: {exc}.") from exc


def record_failure(root: Path, run: LearningRun) -> None:
    """Diagnostic only; never moves the last complete checkpoint pointer."""
    path = root / run.run_id
    if not path.is_dir() or not run.metadata.get("failure"):
        return
    save_status(root, run, "failed")


def load_learning(path: Path) -> LearningRun:
    try:
        base = learning_metadata(path)
        config = LearningConfig(**base["configuration"])
        pointer_path = path / "latest.json"
        if pointer_path.exists():
            pointer = json.loads(_read(pointer_path))
        elif base["schema_version"] == 3 and not (path / "prepared").exists() and not any(path.glob("iteration-*")):
            pointer = {"schema_version": 3, "iteration": -1, "status": "preparing"}
        else:
            raise IntegrityError("Missing artifact: latest.json. Restore the original run directory.")
        if not isinstance(pointer, dict):
            raise IntegrityError("The latest complete iteration pointer must be a JSON object.")
        last = pointer["iteration"]
        if (type(last) is not int or not -1 <= last <= config.total_budget - 8
                or pointer["schema_version"] not in (2, 3)
                or pointer.get("status") not in {"preparing", "running", "paused", "complete", "failed"}):
            raise IntegrityError("Invalid latest complete iteration pointer.")
        run = LearningRun(base, candidate_pool(config), None, None)
        if last >= 0:
            prepared = path / "prepared" if base["schema_version"] == 3 else path
            evaluation = EvaluationSet.from_dict(json.loads(_verified(prepared, "evaluation.json")))
            if base["schema_version"] == 3:
                base.update(json.loads(_verified(prepared, "reference.json")))
            if base["evaluation_identity"] != evaluation.identity or not base["reference_validation"]["passed"]:
                raise IntegrityError("Evaluation identity or reference validation differs from the stored protocol.")
            with np.load(io.BytesIO(_verified(prepared, "trajectory.npz")), allow_pickle=False) as data:
                slices = tuple(Trajectory(float(gamma), data["times"], states) for gamma, states in
                               zip(np.linspace(0, config.gamma_max, config.grid_size), data["states"]))
            if len(slices) != config.grid_size or any(not np.array_equal(item.times, np.linspace(0, config.time_max, 201)) for item in slices):
                raise IntegrityError("Visualization slices differ from the protocol.")
            for item in slices:
                require_valid(item)
            run.evaluation, run.visualization_slices = evaluation, slices
            run.trajectory = slices[config.grid_size // 2]
        for index in range(last + 1):
            folder = path / f"iteration-{index:03d}"
            if folder.is_symlink():
                raise IntegrityError("Symbolic-link checkpoints are unsupported.")
            record = json.loads(_verified(folder, "checkpoint.json"))
            if record["iteration"] != index:
                raise IntegrityError("Checkpoint iteration does not match its directory.")
            strategies = {}
            for name in STRATEGIES:
                stored = record["strategies"][name]
                model = SurrogateModel.from_dict(json.loads(_verified(folder, f"{name}-model.json")))
                observations = tuple(Observation(**item) for item in stored["observations"])
                ids = [item.candidate_id for item in observations]
                if (len(ids) != index + 8 or len(set(ids)) != len(ids)
                        or any(type(i) is not int or not 0 <= i < len(run.candidates) for i in ids)
                        or not np.array_equal(model.scale, [config.gamma_max, config.time_max])
                        or not np.array_equal(model.training_scaled, run.candidates[ids] / model.scale)):
                    raise IntegrityError("Acquired observations or model preprocessing differ from the protocol.")
                arrays = {key: np.asarray(stored[key], dtype=float) for key in
                          ("candidate_mean", "candidate_std", "evaluation_mean", "evaluation_std")}
                for points, prefix in ((run.candidates, "candidate"), (evaluation.points, "evaluation")):
                    mean, std = model.predict(points)
                    if (not np.allclose(mean, arrays[f"{prefix}_mean"], atol=1e-8, rtol=0)
                            or not np.allclose(std, arrays[f"{prefix}_std"], atol=1e-8, rtol=0)):
                        raise IntegrityError("Reloaded model predictions differ from the saved revision by more than 1e-8.")
                if evaluate(arrays["evaluation_mean"], arrays["evaluation_std"], evaluation) != stored["metrics"]:
                    raise IntegrityError("Stored metrics differ from held-out predictions.")
                strategies[name] = StrategyState(observations, model, **arrays, metrics=stored["metrics"],
                                                 selection=stored["selection"], next_selection=stored["next_selection"])
            if index == 0 and strategies["adaptive"].observations != strategies["random"].observations:
                raise IntegrityError("The initial observations are not shared.")
            if record["counts"]["acquired_labels"] != {name: index + 8 for name in STRATEGIES}:
                raise IntegrityError("Recorded budgets disagree with the checkpoint.")
            rng = np.random.default_rng()
            rng.bit_generator.state = record["random_state"]
            if index and any(strategies[name].observations[:-1] != run.latest.strategies[name].observations
                             for name in STRATEGIES):
                raise IntegrityError("A revision changed previously acquired observations.")
            run.checkpoints.append(IterationCheckpoint(index, strategies, record["counts"], record["elapsed_seconds"],
                                                        record["random_state"], record["created_at"]))
        if last + 8 == config.total_budget:
            run.metadata["status"] = "complete"
        elif pointer["status"] in {"paused", "failed"}:
            run.metadata["status"] = pointer["status"]
        else:
            run.metadata["status"] = "interrupted"
        if pointer.get("failure"):
            run.metadata["failure"] = pointer["failure"]
        # Older phase-two diagnostics remain readable, but a successful continuation
        # supersedes a diagnostic from an earlier checkpoint.
        if base["schema_version"] == 2 and (path / "failure.json").exists():
            failure = json.loads(_read(path / "failure.json"))
            if pointer["status"] == "failed" or failure.get("latest_complete_iteration") == last and pointer["status"] == "running":
                run.metadata["failure"], run.metadata["status"] = failure, "failed"
        return run
    except RepositoryError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise IntegrityError(f"Cannot open this learning result: {exc}. Original files were preserved.") from exc
