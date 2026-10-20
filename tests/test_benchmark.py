"""Phase-four evidence through public preparation, aggregation and dashboard APIs."""
import csv
import io
import json
from pathlib import Path
import shutil

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from qentis.benchmark import (benchmark_csv, load_benchmark, prepare_benchmark,
                              prepare_presentation, summarize_benchmark)
from qentis.config import LearningConfig
from qentis.repository import RepositoryError, RunRepository


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    root = tmp_path_factory.mktemp('prepared-benchmark')
    prepare_presentation(root)
    prepare_benchmark(root)
    return root


def test_prepared_benchmark_retains_all_fixed_seeds_and_equal_budgets(prepared):
    data = load_benchmark(prepared)
    assert [row['seed'] for row in data['outcomes']] == list(range(10))
    assert [row['status'] for row in data['outcomes']] == ['complete'] * 10
    assert len({row['evaluation_identity'] for row in data['outcomes']}) == 1
    repository = RunRepository(prepared)
    for row in data['outcomes']:
        run = repository.load(row['run_id'])
        assert run.config == LearningConfig(seed=row['seed'], total_budget=32)
        assert len(run.checkpoints) == 25
        assert [len(run.latest.strategies[name].observations) for name in ('adaptive', 'random')] == [32, 32]
        for name in ('adaptive', 'random'):
            assert row['rmse'][name] == [step.strategies[name].metrics['rmse'] for step in run.checkpoints]


def test_aggregation_keeps_losses_and_failures_outside_mean_denominator():
    rows = []
    # Exact binary fractions make the mean and population SD independently checkable.
    for seed, adaptive, random in [(0, .125, .25), (1, .5, .25), (2, .25, .25), (3, .25 + 5e-9, .25)]:
        rows.append({'seed': seed, 'status': 'complete', 'rmse': {'adaptive': [adaptive] * 25, 'random': [random] * 25}})
    rows.extend({'seed': seed, 'status': 'failed', 'failure': 'Numerical reference unavailable'} for seed in range(4, 10))
    result = summarize_benchmark({'outcomes': rows})
    assert (result['completed'], result['failed'], result['wins'], result['ties'], result['losses']) == (4, 6, 1, 2, 1)
    values = [.125, .5, .25, .25 + 5e-9]
    assert result['curves']['adaptive']['mean'] == [np.mean(values)] * 25
    assert result['curves']['adaptive']['std'] == [np.std(values, ddof=0)] * 25
    assert result['mean_final_difference'] == np.mean(np.array(values) - .25)


def test_preparation_relaunch_preserves_all_terminal_outcomes_byte_for_byte(prepared):
    path = prepared / 'benchmark.json'
    before = path.read_bytes()
    run_ids = [row['run_id'] for row in load_benchmark(prepared)['outcomes']]
    result = prepare_benchmark(prepared)
    assert path.read_bytes() == before
    assert [row['run_id'] for row in result['outcomes']] == run_ids
    assert len(RunRepository(prepared).list_runs()) == 11


def test_failed_seed_is_retained_without_replacement_on_relaunch(tmp_path, monkeypatch):
    from sklearn.gaussian_process import GaussianProcessRegressor
    original = GaussianProcessRegressor.fit
    def unavailable_fit(self, *args, **kwargs):
        raise ValueError('External optimizer unavailable')
    monkeypatch.setattr(GaussianProcessRegressor, 'fit', unavailable_fit)
    result = prepare_benchmark(tmp_path)
    assert [row['status'] for row in result['outcomes']] == ['failed'] * 10
    assert all('External optimizer unavailable' in row['failure'] for row in result['outcomes'])
    before = (tmp_path / 'benchmark.json').read_bytes()
    monkeypatch.setattr(GaussianProcessRegressor, 'fit', original)
    prepare_benchmark(tmp_path)
    assert (tmp_path / 'benchmark.json').read_bytes() == before
    summary = summarize_benchmark(load_benchmark(tmp_path))
    assert (summary['completed'], summary['failed'], summary['curves']) == (0, 10, {})
    assert len(RunRepository(tmp_path).list_runs()) == 10


def test_interrupted_summary_write_recovers_confirmed_seed_without_new_run(tmp_path, monkeypatch):
    import os
    original = os.replace
    rejected = False
    def interrupt_summary(source, destination):
        nonlocal rejected
        if Path(destination).name == 'benchmark.json' and not rejected:
            data = json.loads(Path(source).read_text())
            if data['outcomes'][0]['status'] == 'complete':
                rejected = True
                raise OSError('Presentation disk temporarily unavailable')
        return original(source, destination)
    monkeypatch.setattr(os, 'replace', interrupt_summary)
    with pytest.raises(OSError, match='temporarily unavailable'):
        prepare_benchmark(tmp_path)
    interrupted = load_benchmark(tmp_path)
    first_id = interrupted['outcomes'][0]['run_id']
    first = RunRepository(tmp_path).load(first_id)
    assert first.metadata['status'] == 'complete'
    checkpoint = tmp_path / first_id / 'iteration-024/checkpoint.json'
    before = checkpoint.read_bytes()
    monkeypatch.setattr(os, 'replace', original)
    recovered = prepare_benchmark(tmp_path)
    assert [row['status'] for row in recovered['outcomes']] == ['complete'] * 10
    assert recovered['outcomes'][0]['run_id'] == first_id
    assert checkpoint.read_bytes() == before
    assert len(RunRepository(tmp_path).list_runs()) == 10


def test_benchmark_download_contains_every_seed_and_each_completed_budget(prepared):
    data = load_benchmark(prepared)
    rows = list(csv.DictReader(io.StringIO(benchmark_csv(data).decode())))
    assert len(rows) == 250
    for seed in range(10):
        selected = [row for row in rows if int(row['seed']) == seed]
        assert [int(row['acquired_labels_per_strategy']) for row in selected] == list(range(8, 33))
        assert [float(row['adaptive_rmse']) for row in selected] == data['outcomes'][seed]['rmse']['adaptive']
        assert [float(row['random_rmse']) for row in selected] == data['outcomes'][seed]['rmse']['random']


def test_damaged_or_invented_summary_is_rejected_while_original_evidence_survives(prepared, tmp_path):
    shutil.copytree(prepared, tmp_path / 'evidence')
    root = tmp_path / 'evidence'
    path = root / 'benchmark.json'
    data = json.loads(path.read_text())
    run_id = data['outcomes'][0]['run_id']
    data['outcomes'][0]['rmse']['adaptive'][-1] = .000001
    path.write_text(json.dumps(data))
    with pytest.raises(RepositoryError, match='summary differs'):
        load_benchmark(root)
    assert RunRepository(root).load(run_id).metadata['status'] == 'complete'


def test_saved_opening_and_all_benchmark_seeds_are_inspectable_in_both_themes(prepared, monkeypatch):
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(prepared))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30).run()
    next(button for button in app.button if button.label == 'Open saved run').click().run()
    assert not app.exception
    assert app.session_state['result_source'] == 'saved'
    assert app.session_state['active_run'].run_id == json.loads((prepared / 'presentation.json').read_text())['run_id']
    app.radio(key='view').set_value('Benchmark').run()
    assert not app.exception
    assert any('10/10 complete' in text.value for text in app.markdown)
    selector = next(item for item in app.selectbox if item.label == 'Inspect seed (all outcomes)')
    assert selector.options == [f'Seed {seed} · complete' for seed in range(10)]
    selector.set_value(6).run()
    next(button for button in app.button if button.label == 'Open seed evidence').click().run()
    assert not app.exception
    assert any('Random lower' in caption.value for caption in app.caption)
    app.toggle(key='dark_mode').set_value(False).run()
    assert not app.exception
    assert any('Fixed benchmark protocol' in item.value for item in app.info)


def test_local_preparation_prediction_and_exports_do_not_require_external_network(tmp_path, monkeypatch):
    import socket
    original_connect = socket.socket.connect
    def no_external(self, address):
        if isinstance(address, tuple) and address[0] not in ('127.0.0.1', 'localhost', '::1'):
            raise AssertionError(f'External network requested: {address[0]}')
        return original_connect(self, address)
    monkeypatch.setattr(socket.socket, 'connect', no_external)
    monkeypatch.setattr(socket, 'create_connection', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('Network requested')))
    record = prepare_presentation(tmp_path)
    run = RunRepository(tmp_path).load(record['run_id'])
    from qentis.exports import export_evidence
    evidence = export_evidence(run)
    assert len(evidence) == 3
    for state in run.latest.strategies.values():
        mean, std = state.model.predict([[1., 2.5]])
        assert np.isfinite(mean).all() and np.isfinite(std).all()
    assert record['target_met'] == (record['wall_seconds'] <= 60)
    assert prepare_presentation(tmp_path) == record
    assert len(RunRepository(tmp_path).list_runs()) == 1


def test_empty_library_benchmark_and_opening_have_real_recovery_guidance(tmp_path, monkeypatch):
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(tmp_path))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py').run()
    assert not app.exception
    assert any('No prepared presentation result' in item.value for item in app.caption)
    app.radio(key='view').set_value('Benchmark').run()
    assert not app.exception
    assert any('No prepared benchmark' in item.value for item in app.info)
    assert not [button for button in app.button if button.label == 'Open seed evidence']


@pytest.mark.parametrize('damage', ['unknown-schema', 'truncated-history', 'missing-checkpoint'])
def test_damaged_benchmark_has_specific_recovery_message_without_dashboard_exception(prepared, tmp_path, monkeypatch, damage):
    root = tmp_path / 'evidence'
    shutil.copytree(prepared, root)
    path = root / 'benchmark.json'
    original = path.read_bytes()
    data = json.loads(original)
    if damage == 'unknown-schema':
        data['schema_version'] = 999
        path.write_text(json.dumps(data))
    elif damage == 'truncated-history':
        data['outcomes'][0]['rmse']['adaptive'] = []
        path.write_text(json.dumps(data))
    else:
        (root / data['outcomes'][0]['run_id'] / 'iteration-024/checkpoint.json').unlink()
    before = path.read_bytes()
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(root))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py').run()
    app.radio(key='view').set_value('Benchmark').run()
    assert not app.exception
    assert any('Cannot open prepared benchmark' in error.value for error in app.error)
    assert path.read_bytes() == before
