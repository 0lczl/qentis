"""Durability and failure behavior through the local run repository."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from qentis.config import ExperimentConfig
from qentis.experiment import create_run
from qentis.repository import CompatibilityError, IntegrityError, RepositoryError, RunRepository


@pytest.fixture
def saved_run(tmp_path):
    repository = RunRepository(tmp_path / "results")
    run = create_run(ExperimentConfig())
    repository.save(run)
    return repository, run


def change_metadata(repository, run, change):
    """Edit a disposable record with an intact manifest to exercise schema checks."""
    path = repository.root / run.run_id
    metadata = json.loads((path / "run.json").read_text())
    change(metadata)
    raw = json.dumps(metadata).encode()
    (path / "run.json").write_bytes(raw)
    manifest = json.loads((path / "manifest.json").read_text())
    manifest["artifacts"]["run.json"] = {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
    (path / "manifest.json").write_text(json.dumps(manifest))


def test_a_fresh_process_reopens_the_exact_states_and_original_provenance(saved_run):
    repository, run = saved_run
    script = '''
import json, sys
from hashlib import sha256
from qentis.repository import RunRepository
run = RunRepository(sys.argv[1]).load(sys.argv[2])
print(json.dumps({"metadata": run.metadata, "states": sha256(run.trajectory.states.tobytes()).hexdigest(),
                  "times": run.trajectory.times.tolist()}))
'''
    result = subprocess.run([sys.executable, "-c", script, str(repository.root), run.run_id],
                            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
                            check=True, timeout=20)
    loaded = json.loads(result.stdout)
    assert loaded["metadata"] == run.metadata
    assert loaded["states"] == sha256(run.trajectory.states.tobytes()).hexdigest()
    assert loaded["times"] == run.trajectory.times.tolist()


def test_new_settings_create_another_run_without_rewriting_history(saved_run):
    repository, first = saved_run
    second = create_run(ExperimentConfig(gamma=0))
    repository.save(second)
    assert first.run_id != second.run_id
    assert {summary.run_id for summary in repository.list_runs()} == {first.run_id, second.run_id}
    assert repository.load(first.run_id).config.gamma == 1.0
    assert repository.load(second.run_id).config.gamma == 0.0


@pytest.mark.parametrize("artifact", ["run.json", "trajectory.npz", "manifest.json"])
def test_a_missing_artifact_is_explained_and_original_files_are_preserved(saved_run, artifact):
    repository, run = saved_run
    path = repository.root / run.run_id
    (path / artifact).unlink()
    with pytest.raises(IntegrityError, match="Missing artifact: " + artifact):
        repository.load(run.run_id)
    assert path.is_dir()


@pytest.mark.parametrize("artifact", ["run.json", "trajectory.npz"])
def test_changed_artifact_bytes_are_rejected_by_the_checksum(saved_run, artifact):
    repository, run = saved_run
    path = repository.root / run.run_id / artifact
    path.write_bytes(path.read_bytes() + b"corruption")
    with pytest.raises(IntegrityError, match="Checksum mismatch: " + artifact):
        repository.load(run.run_id)
    assert path.read_bytes().endswith(b"corruption")


def test_an_unknown_schema_requires_the_original_application(saved_run):
    repository, run = saved_run
    change_metadata(repository, run, lambda metadata: metadata.update(schema_version=999))
    with pytest.raises(CompatibilityError, match="Unsupported run schema"):
        repository.load(run.run_id)


def test_dependency_mismatch_never_silently_changes_the_saved_protocol(saved_run):
    repository, run = saved_run
    change_metadata(repository, run, lambda metadata: metadata["provenance"]["dependencies"].update(qutip="0.0.0"))
    with pytest.raises(CompatibilityError, match="Dependency versions differ"):
        repository.load(run.run_id)


def test_interrupted_atomic_commit_preserves_the_last_complete_result(saved_run, monkeypatch):
    repository, first = saved_run
    second = create_run(ExperimentConfig(gamma=0))
    def failed_rename(*args, **kwargs):
        raise OSError("simulated interrupted filesystem commit")
    monkeypatch.setattr(os, "replace", failed_rename)
    with pytest.raises(RepositoryError, match="not confirmed saved"):
        repository.save(second)
    assert [summary.run_id for summary in repository.list_runs()] == [first.run_id]
    np.testing.assert_array_equal(repository.load(first.run_id).trajectory.states, first.trajectory.states)


def test_a_save_to_an_unwritable_location_is_not_reported_as_success(tmp_path):
    location = tmp_path / "results"
    location.write_text("a file occupies the requested directory")
    repository = RunRepository(location)
    with pytest.raises(RepositoryError, match="not confirmed saved"):
        repository.save(create_run(ExperimentConfig()))
    assert location.read_text() == "a file occupies the requested directory"


def test_existing_run_ids_cannot_be_overwritten(saved_run):
    repository, run = saved_run
    with pytest.raises(RepositoryError, match="already exists"):
        repository.save(run)
    assert [summary.run_id for summary in repository.list_runs()] == [run.run_id]
    assert repository.load(run.run_id).metadata == run.metadata


def test_an_empty_library_and_abandoned_staging_folders_are_not_fabricated_results(tmp_path):
    repository = RunRepository(tmp_path / "results")
    assert repository.list_runs() == []
    (repository.root / ".pending-interrupted").mkdir(parents=True)
    (repository.root / ".pending-interrupted" / "run.json").write_text("incomplete")
    assert repository.list_runs() == []
