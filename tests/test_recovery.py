"""Recovery and exports through public engine, runtime, and storage interfaces."""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event

import numpy as np
import pytest

from qentis.config import LearningConfig
from qentis.exports import export_evidence
from qentis.learning import (LearningFailure, advance_comparison, new_comparison,
                            resume_comparison, run_comparison)
from qentis.repository import IntegrityError, RepositoryError, RunRepository
from qentis.runtime import LearningSession, RunBusy


@pytest.mark.parametrize('seed', [0, 2])
def test_paused_reloaded_continuation_matches_uninterrupted_science(tmp_path, seed):
    config = LearningConfig(seed=seed, grid_size=7, total_budget=16)
    repository = RunRepository(tmp_path / 'resumed')
    pause = Event()
    def commit(run):
        repository.save_checkpoint(run)
        if run.latest.iteration == 3:
            pause.set()
    paused = run_comparison(config, commit, pause_requested=pause.is_set)
    assert paused.metadata['status'] == 'paused'
    loaded = repository.load(paused.run_id)
    assert loaded.metadata['status'] == 'paused'
    assert loaded.latest.counts['acquired_labels'] == {'adaptive': 11, 'random': 11}
    completed = resume_comparison(loaded, repository.save_checkpoint)
    expected = run_comparison(config, RunRepository(tmp_path / 'uninterrupted').save_checkpoint)
    assert completed.metadata['status'] == 'complete'
    for actual, original in zip(completed.checkpoints, expected.checkpoints, strict=True):
        assert actual.counts == original.counts
        assert actual.random_state == original.random_state
        for name in ('adaptive', 'random'):
            assert actual.strategies[name].observations == original.strategies[name].observations
            assert actual.strategies[name].selection == original.strategies[name].selection
            for key, value in original.strategies[name].metrics.items():
                assert actual.strategies[name].metrics[key] == pytest.approx(value, abs=1e-8, rel=0)


def test_fresh_process_recovers_interrupted_checkpoint_and_continues_same_protocol(tmp_path):
    code = '''
import os,sys
from qentis.config import LearningConfig
from qentis.learning import new_comparison,advance_comparison
from qentis.repository import RunRepository
repository=RunRepository(sys.argv[1])
run=new_comparison(LearningConfig(seed=3,grid_size=5,total_budget=12))
repository.begin_learning(run)
advance_comparison(run,repository.save_checkpoint)
advance_comparison(run,repository.save_checkpoint)
print(run.run_id,flush=True)
os._exit(0)
'''
    result = subprocess.run([sys.executable, '-c', code, str(tmp_path / 'interrupted')],
                            check=True, capture_output=True, text=True)
    repository = RunRepository(tmp_path / 'interrupted')
    loaded = repository.load(result.stdout.strip())
    assert loaded.metadata['status'] == 'interrupted'
    assert loaded.latest.iteration == 1
    session = LearningSession(repository.root)
    assert session.resume(loaded.run_id) == loaded.run_id
    snapshot = session.wait(20)
    assert not snapshot.active
    assert snapshot.error is None
    expected = run_comparison(loaded.config, RunRepository(tmp_path / 'uninterrupted').save_checkpoint)
    actual = repository.load(loaded.run_id)
    assert actual.metadata['status'] == 'complete'
    for name in ('adaptive', 'random'):
        assert actual.latest.strategies[name].observations == expected.latest.strategies[name].observations
        assert actual.latest.strategies[name].metrics == expected.latest.strategies[name].metrics


def test_interruption_before_first_checkpoint_retains_settings_but_requires_new_restart(tmp_path):
    repository = RunRepository(tmp_path)
    original = new_comparison(LearningConfig(seed=7, grid_size=5, total_budget=10))
    repository.begin_learning(original)
    loaded = repository.load(original.run_id)
    assert loaded.metadata['status'] == 'interrupted'
    assert loaded.checkpoints == []
    assert loaded.config == original.config
    session = LearningSession(tmp_path)
    with pytest.raises(RepositoryError, match='No complete learning checkpoint'):
        session.resume(loaded.run_id)
    new_id = session.start(loaded.config)
    snapshot = session.wait(20)
    assert snapshot.error is None
    assert new_id != original.run_id
    assert repository.load(new_id).metadata['status'] == 'complete'
    assert repository.load(original.run_id).metadata['status'] == 'interrupted'
    assert len(repository.list_runs()) == 2


def test_live_pause_finishes_both_strategies_and_blocks_a_second_writer(tmp_path, monkeypatch):
    from sklearn.gaussian_process import GaussianProcessRegressor
    original_fit = GaussianProcessRegressor.fit
    fitting, release = Event(), Event()
    attempts = 0
    def held_fit(self, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            fitting.set()
            assert release.wait(10), 'test did not release external fitting boundary'
        return original_fit(self, *args, **kwargs)
    monkeypatch.setattr(GaussianProcessRegressor, 'fit', held_fit)
    session = LearningSession(tmp_path)
    run_id = session.start(LearningConfig(grid_size=5, total_budget=12))
    try:
        assert fitting.wait(10)
        before = session.snapshot()
        assert before.active
        assert before.run.latest.iteration == 0
        with pytest.raises(RunBusy, match='another session'):
            LearningSession(tmp_path).start(LearningConfig())
        session.request_pause()
    finally:
        release.set()
    stopped = session.wait(20)
    assert not stopped.active
    assert stopped.error is None
    assert stopped.run.metadata['status'] == 'paused'
    loaded = RunRepository(tmp_path).load(run_id)
    assert loaded.metadata['status'] == 'paused'
    assert loaded.latest.counts['acquired_labels'] == {'adaptive': 9, 'random': 9}
    assert len(loaded.checkpoints) == 2


def test_resume_after_unconfirmed_revision_write_preserves_previous_history(tmp_path, monkeypatch):
    repository = RunRepository(tmp_path / 'recovery')
    original_replace = os.replace
    failed = False
    def interrupted_pointer(source, destination):
        nonlocal failed
        if Path(destination).name == 'latest.json' and json.loads(Path(source).read_text())['iteration'] == 1 and not failed:
            failed = True
            raise OSError('disk unavailable before pointer confirmation')
        return original_replace(source, destination)
    with monkeypatch.context() as patch:
        patch.setattr(os, 'replace', interrupted_pointer)
        with pytest.raises(LearningFailure, match='not confirmed saved') as failure:
            run_comparison(LearningConfig(seed=4, grid_size=5, total_budget=11), repository.save_checkpoint)
    run = failure.value.run
    assert run.latest.iteration == 0
    folder = repository.root / run.run_id
    unchanged = {path: path.read_bytes() for path in (folder / 'run.json', folder / 'iteration-000/checkpoint.json')}
    unconfirmed = (folder / 'iteration-001/checkpoint.json').read_bytes()
    loaded = repository.load(run.run_id)
    assert loaded.latest.iteration == 0
    resumed = resume_comparison(loaded, repository.save_checkpoint)
    expected = run_comparison(loaded.config, RunRepository(tmp_path / 'expected').save_checkpoint)
    assert repository.load(run.run_id).metadata['status'] == 'complete'
    assert all(path.read_bytes() == value for path, value in unchanged.items())
    assert any(path.read_bytes() == unconfirmed for path in folder.glob('.unconfirmed-*/checkpoint.json'))
    for name in ('adaptive', 'random'):
        assert resumed.latest.strategies[name].observations == expected.latest.strategies[name].observations
        assert resumed.latest.strategies[name].metrics == expected.latest.strategies[name].metrics


@pytest.mark.parametrize('revision', [0, 2])
def test_json_and_csv_exports_match_the_selected_confirmed_revision(tmp_path, revision):
    run = run_comparison(LearningConfig(seed=5, grid_size=5, total_budget=11), RunRepository(tmp_path).save_checkpoint)
    exported = export_evidence(run, revision)
    record = json.loads(exported['configuration'].content)
    checkpoint = run.checkpoints[revision]
    assert record['run_id'] == run.run_id
    assert record['configuration'] == run.config.to_dict()
    assert record['counts'] == checkpoint.counts
    assert record['selected_iteration'] == revision
    assert record['provenance'] == run.metadata['provenance']
    assert record['evaluation_identity'] == run.evaluation.identity
    rows = list(csv.DictReader(io.StringIO(exported['observations'].content.decode())))
    assert len(rows) == 2 * (8 + revision)
    for name in ('adaptive', 'random'):
        selected = [row for row in rows if row['strategy'] == name]
        assert [int(row['candidate_id']) for row in selected] == checkpoint.strategies[name].ids
        for row, observation in zip(selected, checkpoint.strategies[name].observations, strict=True):
            assert float(row['numerical_coherence_x']) == observation.value
            assert row['shared_initial'] == str(int(row['acquired_order']) <= 8)
            np.testing.assert_array_equal([float(row['gamma_inverse_time_units']), float(row['time_dimensionless_units'])],
                                          run.candidates[observation.candidate_id])
    metrics = list(csv.DictReader(io.StringIO(exported['metrics'].content.decode())))
    assert len(metrics) == 2 * (revision + 1)
    for row in metrics:
        step = int(row['iteration'])
        assert int(row['labels_per_strategy']) == step + 8
        for key, value in run.checkpoints[step].strategies[row['strategy']].metrics.items():
            assert float(row[key]) == value
    assert all(f'revision-{revision:03d}' in file.filename for file in exported.values())


def test_phase_two_learning_record_remains_reloadable_and_can_continue(tmp_path):
    original = run_comparison(LearningConfig(seed=1, grid_size=5, total_budget=10), lambda run: None)
    original.metadata['schema_version'] = 2
    history = list(original.checkpoints)
    original.checkpoints = history[:1]
    original.metadata['status'] = 'running'
    repository = RunRepository(tmp_path)
    repository.save_checkpoint(original)
    loaded = repository.load(original.run_id)
    assert loaded.metadata['schema_version'] == 2
    assert loaded.metadata['status'] == 'interrupted'
    resumed = resume_comparison(loaded, repository.save_checkpoint)
    final = repository.load(resumed.run_id)
    assert final.metadata['status'] == 'complete'
    for name in ('adaptive', 'random'):
        assert final.latest.strategies[name].observations == history[-1].strategies[name].observations
        assert final.latest.strategies[name].metrics == history[-1].strategies[name].metrics


def test_preparation_failure_is_recorded_without_a_false_checkpoint(tmp_path, monkeypatch):
    import qutip
    def failed_solver(*args, **kwargs):
        raise RuntimeError('numerical reference unavailable')
    monkeypatch.setattr(qutip, 'mesolve', failed_solver)
    session = LearningSession(tmp_path)
    run_id = session.start(LearningConfig(seed=9))
    snapshot = session.wait(20)
    assert not snapshot.active
    assert 'numerical reference unavailable' in snapshot.error
    loaded = RunRepository(tmp_path).load(run_id)
    assert loaded.metadata['status'] == 'failed'
    assert loaded.checkpoints == []
    assert loaded.config.seed == 9
    assert 'numerical reference unavailable' in loaded.metadata['failure']['message']


def test_killed_worker_releases_writer_lock_and_retains_last_complete_pair(tmp_path):
    code = '''
import os,sys
from threading import Event
from sklearn.gaussian_process import GaussianProcessRegressor
from qentis.config import LearningConfig
from qentis.runtime import LearningSession
ready=Event()
original=GaussianProcessRegressor.fit
attempts=0
def held_fit(self,*args,**kwargs):
    global attempts
    attempts+=1
    if attempts==2:
        ready.set()
        Event().wait(60)
    return original(self,*args,**kwargs)
GaussianProcessRegressor.fit=held_fit
session=LearningSession(sys.argv[1])
run_id=session.start(LearningConfig(seed=6,grid_size=5,total_budget=10))
assert ready.wait(10)
print(run_id,flush=True)
Event().wait(60)
'''
    child = subprocess.Popen([sys.executable, '-c', code, str(tmp_path)], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
    try:
        run_id = child.stdout.readline().strip()
        assert run_id.startswith('qentis-')
        with pytest.raises(RunBusy, match='another session'):
            LearningSession(tmp_path).start(LearningConfig())
    finally:
        child.kill()
        child.communicate(timeout=10)
    repository = RunRepository(tmp_path)
    loaded = repository.load(run_id)
    assert loaded.metadata['status'] == 'interrupted'
    assert loaded.latest.iteration == 0
    resumed = LearningSession(tmp_path)
    resumed.resume(run_id)
    assert resumed.wait(20).error is None
    assert repository.load(run_id).metadata['status'] == 'complete'


@pytest.mark.parametrize('damage', ['missing-pointer', 'invalid-pointer', 'missing-model', 'unknown-schema'])
def test_unavailable_checkpoint_blocks_resume_without_changing_original_files(tmp_path, damage):
    repository = RunRepository(tmp_path)
    run = run_comparison(LearningConfig(grid_size=5, total_budget=10), repository.save_checkpoint,
                         pause_requested=lambda: True)
    folder = tmp_path / run.run_id
    if damage == 'missing-pointer':
        (folder / 'latest.json').unlink()
    elif damage == 'invalid-pointer':
        (folder / 'latest.json').write_text('[]')
    elif damage == 'missing-model':
        (folder / 'iteration-000/adaptive-model.json').unlink()
    else:
        manifest = json.loads((folder / 'manifest.json').read_text())
        manifest['schema_version'] = 99
        (folder / 'manifest.json').write_text(json.dumps(manifest))
    original = {path: path.read_bytes() for path in folder.rglob('*') if path.is_file()}
    with pytest.raises(RepositoryError):
        LearningSession(tmp_path).resume(run.run_id)
    assert {path: path.read_bytes() for path in folder.rglob('*') if path.is_file()} == original


def test_failed_pair_can_resume_after_external_fit_recovers_without_budget_drift(tmp_path, monkeypatch):
    from sklearn.gaussian_process import GaussianProcessRegressor
    original_fit = GaussianProcessRegressor.fit
    attempts = 0
    def failed_random_fit(self, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 3:
            raise ValueError('external optimizer unavailable')
        return original_fit(self, *args, **kwargs)
    session = LearningSession(tmp_path / 'recovered')
    config = LearningConfig(seed=2, grid_size=5, total_budget=10)
    with monkeypatch.context() as patch:
        patch.setattr(GaussianProcessRegressor, 'fit', failed_random_fit)
        run_id = session.start(config)
        assert 'external optimizer unavailable' in session.wait(20).error
    repository = RunRepository(tmp_path / 'recovered')
    failed = repository.load(run_id)
    assert failed.metadata['status'] == 'failed'
    assert failed.latest.iteration == 0
    session.resume(run_id)
    assert session.wait(20).error is None
    completed = repository.load(run_id)
    assert completed.metadata['status'] == 'complete'
    assert 'failure' not in completed.metadata
    expected = run_comparison(config, RunRepository(tmp_path / 'expected').save_checkpoint)
    assert completed.latest.counts == expected.latest.counts
    for name in ('adaptive', 'random'):
        assert completed.latest.strategies[name].observations == expected.latest.strategies[name].observations
