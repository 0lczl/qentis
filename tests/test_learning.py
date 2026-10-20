"""Scientific comparison contracts through public interfaces and real computation."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from qentis.config import LearningConfig, ConfigurationError
from qentis.evaluation import EvaluationSet, evaluate
from qentis.learning import LearningFailure, candidate_pool, run_comparison, select_adaptive, select_random
from qentis.physics import reference_point
from qentis.repository import IntegrityError, RunRepository
from qentis.surrogate import SurrogateModel, fit_model


def test_short_preset_has_paired_unique_budgets_and_numerically_acquired_labels(tmp_path):
    repository = RunRepository(tmp_path)
    run = run_comparison(LearningConfig(), repository.save_checkpoint)
    assert len(run.checkpoints) == 17
    assert run.checkpoints[0].strategies['adaptive'].observations == run.checkpoints[0].strategies['random'].observations
    for checkpoint in run.checkpoints:
        expected = 8 + checkpoint.iteration
        assert checkpoint.counts['acquired_labels'] == {'adaptive': expected, 'random': expected}
        for state in checkpoint.strategies.values():
            assert len(state.ids) == len(set(state.ids)) == expected
    for state in run.latest.strategies.values():
        for observation in state.observations:
            gamma, time = run.candidates[observation.candidate_id]
            assert observation.value == reference_point(float(gamma), float(time))
    counts = run.latest.counts
    assert counts['evaluation_solver_calls'] == 400
    assert counts['visualization_solver_calls'] == 21
    assert counts['validation_solver_calls'] == 3
    assert counts['training_solver_calls'] + counts['zero_time_labels'] + counts['cache_hits'] == 48
    assert counts['cache_hits'] >= 8
    assert repository.load(run.run_id).metadata['status'] == 'complete'


def test_model_reload_preserves_preprocessing_and_unclipped_predictions():
    points = np.array([[0, 0], [0.4, 0], [0.8, 0], [0, 2], [0.4, 1], [0.8, 2], [0.2, 0.5], [0.6, 1.5]])
    labels = [reference_point(float(gamma), float(time)) for gamma, time in points]
    model = fit_model(points, labels, [0.8, 2], 7)
    reloaded = SurrogateModel.from_dict(json.loads(json.dumps(model.to_dict())))
    probes = np.array([[0.3, 1.25], [0.7, 0.2], [0.8, 2]])
    expected = model.predict(probes)
    actual = reloaded.predict(probes)
    np.testing.assert_allclose(actual, expected, atol=1e-8, rtol=0)
    np.testing.assert_allclose(model.predict(points)[0], labels, atol=1e-5, rtol=0)
    assert np.all(actual[1] >= 0)
    assert np.isfinite(actual).all()
    # Output values and intervals retain excursions; no physical clipping in prediction.
    assert model.to_dict()['policy']['normalize_y'] is False


def test_adaptive_ties_use_candidate_order_and_exclude_acquired_points():
    config = LearningConfig(grid_size=3, total_budget=8)
    points = candidate_pool(config)[:8]
    model = fit_model(points, [reference_point(float(g), float(t)) for g, t in points], [2, 5], 0)
    candidates = np.repeat([[0.7, 1.3]], 5, axis=0)
    selected, score = select_adaptive(model, candidates, [0, 1])
    assert selected == 2
    assert score == model.predict(candidates[[2]])[1][0]


def test_random_selection_matches_seeded_uniform_sampling_without_replacement():
    candidates = candidate_pool(LearningConfig(grid_size=3, total_budget=8))
    actual_rng = np.random.default_rng(34)
    expected_rng = np.random.default_rng(34)
    acquired = [0, 4]
    while len(acquired) < len(candidates):
        available = np.setdiff1d(np.arange(len(candidates)), acquired)
        expected = int(expected_rng.choice(available))
        actual = select_random(candidates, acquired, actual_rng)
        assert actual == expected
        assert actual not in acquired
        acquired.append(actual)


def test_held_out_labels_are_disjoint_and_cannot_change_the_next_selection(tmp_path):
    run = run_comparison(LearningConfig(grid_size=3, total_budget=8), RunRepository(tmp_path).save_checkpoint)
    original = run.latest.strategies['adaptive']
    expected = select_adaptive(original.model, run.candidates, original.ids)
    assert not any(np.array_equal(a, b) for a in run.candidates for b in run.evaluation.points)
    previous_metrics = evaluate(original.evaluation_mean, original.evaluation_std, run.evaluation)
    run.evaluation = replace(run.evaluation, labels=run.evaluation.labels + 100)
    changed_metrics = evaluate(original.evaluation_mean, original.evaluation_std, run.evaluation)
    assert changed_metrics['rmse'] > 99
    assert changed_metrics != previous_metrics
    assert select_adaptive(original.model, run.candidates, original.ids) == expected


def test_evaluation_reports_known_errors_coverage_and_physical_excursions():
    reference = EvaluationSet(np.array([[0.1, 0.2], [0.2, 0.3]]), np.array([0., 1.]), 'example')
    result = evaluate(np.array([-2., 1.]), np.array([0.1, 0.1]), reference)
    assert result == {'rmse': np.sqrt(2), 'mae': 1., 'max_absolute_error': 2.,
                      'outside_physical_fraction': 0.5, 'interval_coverage': 0.5,
                      'mean_interval_width': 0.392}


@pytest.mark.parametrize('settings', [{'total_budget': 65}, {'total_budget': 7}, {'seed': -1},
                                      {'seed': 1.5}, {'grid_size': 32}, {'gamma_max': 0},
                                      {'time_max': float('nan')}, {'grid_size': 3, 'total_budget': 10}])
def test_unsupported_protocols_are_rejected_before_work(settings):
    with pytest.raises(ConfigurationError):
        LearningConfig(**settings)


def test_identical_seeds_reproduce_selection_sequences_and_metrics(tmp_path):
    runs = [run_comparison(LearningConfig(seed=2, grid_size=5, total_budget=10),
                           RunRepository(tmp_path / str(index)).save_checkpoint) for index in range(2)]
    for name in ('adaptive', 'random'):
        assert runs[0].latest.strategies[name].observations == runs[1].latest.strategies[name].observations
        assert runs[0].latest.strategies[name].metrics == runs[1].latest.strategies[name].metrics


def test_failed_model_fit_discards_the_whole_uncommitted_pair(tmp_path, monkeypatch):
    from sklearn.gaussian_process import GaussianProcessRegressor
    repository = RunRepository(tmp_path)
    original_fit = GaussianProcessRegressor.fit
    attempts = 0
    def fail_random_fit(self, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 3:
            raise ValueError('external optimizer failure')
        return original_fit(self, *args, **kwargs)
    monkeypatch.setattr(GaussianProcessRegressor, 'fit', fail_random_fit)
    with pytest.raises(LearningFailure, match='external optimizer failure') as failure:
        run_comparison(LearningConfig(total_budget=9), repository.save_checkpoint)
    run = failure.value.run
    assert len(run.checkpoints) == 1
    assert run.latest.counts['acquired_labels'] == {'adaptive': 8, 'random': 8}
    repository.record_failure(run)
    loaded = repository.load(run.run_id)
    assert loaded.metadata['status'] == 'failed'
    assert loaded.latest.counts['acquired_labels'] == {'adaptive': 8, 'random': 8}


def test_failed_solver_preserves_the_last_complete_budget(tmp_path, monkeypatch):
    import qutip
    repository = RunRepository(tmp_path)
    def failing_solver(*args, **kwargs):
        raise RuntimeError('numerical backend unavailable')
    def commit(run):
        repository.save_checkpoint(run)
        monkeypatch.setattr(qutip, 'mesolve', failing_solver)
    with pytest.raises(LearningFailure, match='numerical backend unavailable') as failure:
        run_comparison(LearningConfig(total_budget=9), commit)
    loaded = repository.load(failure.value.run.run_id)
    assert loaded.latest.counts['acquired_labels'] == {'adaptive': 8, 'random': 8}
    assert len(loaded.checkpoints) == 1


def test_failed_checkpoint_pointer_write_does_not_advance_saved_budget(tmp_path, monkeypatch):
    repository = RunRepository(tmp_path)
    original_replace = os.replace
    def commit(run):
        if run.latest.iteration == 1:
            def fail_pointer(source, destination):
                if Path(destination).name == 'latest.json':
                    raise OSError('disk write failure')
                return original_replace(source, destination)
            monkeypatch.setattr(os, 'replace', fail_pointer)
        repository.save_checkpoint(run)
    with pytest.raises(LearningFailure, match='not confirmed saved') as failure:
        run_comparison(LearningConfig(total_budget=9), commit)
    assert failure.value.run.latest.iteration == 0
    assert repository.load(failure.value.run.run_id).latest.iteration == 0


def test_fresh_python_process_reloads_model_without_solver_or_training(tmp_path):
    repository = RunRepository(tmp_path)
    run = run_comparison(LearningConfig(grid_size=3, total_budget=8), repository.save_checkpoint)
    expected = run.latest.strategies['adaptive'].model.predict([[0.3, 2.2], [1.8, 4.1]])
    code = """
import json, sys, qutip
from sklearn.gaussian_process import GaussianProcessRegressor
from qentis.repository import RunRepository
def forbidden(*args, **kwargs): raise AssertionError('reload must not compute labels or fit')
qutip.mesolve = forbidden
GaussianProcessRegressor.fit = forbidden
run = RunRepository(sys.argv[1]).load(sys.argv[2])
print(json.dumps([a.tolist() for a in run.latest.strategies['adaptive'].model.predict([[0.3,2.2],[1.8,4.1]])]))
"""
    output = subprocess.run([sys.executable, '-c', code, str(tmp_path), run.run_id],
                            check=True, capture_output=True, text=True)
    np.testing.assert_allclose(json.loads(output.stdout), expected, atol=1e-8, rtol=0)


@pytest.mark.parametrize('artifact', ['adaptive-model.json', 'random-model.json', 'checkpoint.json'])
def test_damaged_learning_revision_is_rejected_without_deleting_files(tmp_path, artifact):
    repository = RunRepository(tmp_path)
    run = run_comparison(LearningConfig(grid_size=3, total_budget=8), repository.save_checkpoint)
    path = tmp_path / run.run_id / 'iteration-000' / artifact
    path.write_bytes(path.read_bytes() + b'corruption')
    with pytest.raises(IntegrityError, match='Checksum mismatch'):
        repository.load(run.run_id)
    assert path.exists()


@pytest.mark.parametrize('artifact', ['prepared/evaluation.json', 'prepared/trajectory.npz', 'iteration-000/adaptive-model.json'])
def test_missing_learning_artifacts_have_specific_errors(tmp_path, artifact):
    repository = RunRepository(tmp_path)
    run = run_comparison(LearningConfig(grid_size=3, total_budget=8), repository.save_checkpoint)
    (tmp_path / run.run_id / artifact).unlink()
    with pytest.raises(IntegrityError, match='Missing artifact'):
        repository.load(run.run_id)
    assert (tmp_path / run.run_id / 'run.json').exists()


def test_unknown_learning_schema_is_not_silently_migrated(tmp_path):
    from qentis.repository import CompatibilityError
    repository = RunRepository(tmp_path)
    run = run_comparison(LearningConfig(grid_size=3, total_budget=8), repository.save_checkpoint)
    path = tmp_path / run.run_id / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest['schema_version'] = 99
    path.write_text(json.dumps(manifest))
    with pytest.raises(CompatibilityError, match='schema'):
        repository.load(run.run_id)
