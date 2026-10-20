"""Recovery controls and evidence downloads through the dashboard interface."""
from pathlib import Path
from threading import Event
import json

from streamlit.testing.v1 import AppTest

from qentis.config import LearningConfig
from qentis.learning import new_comparison, run_comparison
from qentis.repository import RunRepository
from qentis.runtime import learning_session

APP = Path(__file__).resolve().parents[1] / 'app.py'


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()


def open_saved(app, run_id):
    app.radio(key='view').set_value('Saved runs').run()
    app.selectbox[0].set_value(run_id).run()
    click(app, 'Open selected run')


def test_saved_paused_run_resumes_to_completion_without_new_identity(tmp_path, monkeypatch):
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(tmp_path))
    repository = RunRepository(tmp_path)
    run = run_comparison(LearningConfig(grid_size=5, total_budget=12), repository.save_checkpoint,
                         pause_requested=lambda: True)
    app = AppTest.from_file(APP, default_timeout=30).run()
    open_saved(app, run.run_id)
    assert any('Paused · saved paired step 0' in item.value for item in app.info)
    click(app, 'Resume experiment')
    assert learning_session(tmp_path).wait(20).error is None
    app.run()
    assert not app.exception
    assert not app.error
    assert repository.load(run.run_id).metadata['status'] == 'complete'
    assert app.select_slider[0].value == 4
    assert [item.run_id for item in repository.list_runs()] == [run.run_id]
    assert any('complete' in item.value for item in app.markdown)


def test_live_pause_survives_theme_redraw_and_stops_at_one_whole_new_pair(tmp_path, monkeypatch):
    from sklearn.gaussian_process import GaussianProcessRegressor
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(tmp_path))
    fitting, release = Event(), Event()
    original_fit = GaussianProcessRegressor.fit
    attempts = 0
    def held_fit(self, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            fitting.set()
            assert release.wait(15)
        return original_fit(self, *args, **kwargs)
    monkeypatch.setattr(GaussianProcessRegressor, 'fit', held_fit)
    app = AppTest.from_file(APP, default_timeout=30).run()
    click(app, 'Run experiment')
    session = learning_session(tmp_path)
    try:
        assert fitting.wait(10)
        run_id = session.snapshot().run.run_id
        assert next(button for button in app.button if button.label == 'Run experiment').disabled
        app.toggle(key='dark_mode').set_value(False).run()
        assert session.snapshot().run.run_id == run_id
        click(app, 'Pause after this step')
        assert session.snapshot().pause_requested
    finally:
        release.set()
    assert session.wait(20).error is None
    app.run()
    assert not app.exception
    assert not app.error
    assert any('Paused · saved paired step 1' in item.value for item in app.info)
    run = RunRepository(tmp_path).load(run_id)
    assert run.latest.counts['acquired_labels'] == {'adaptive': 9, 'random': 9}
    assert len(RunRepository(tmp_path).list_runs()) == 1
    assert not next(button for button in app.button if button.label == 'Run experiment').disabled


def test_run_without_checkpoint_offers_restart_and_preserves_original_record(tmp_path, monkeypatch):
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(tmp_path))
    repository = RunRepository(tmp_path)
    original = new_comparison(LearningConfig(seed=8, grid_size=5, total_budget=10))
    repository.begin_learning(original)
    metadata = tmp_path / original.run_id / 'run.json'
    unchanged = metadata.read_bytes()
    app = AppTest.from_file(APP, default_timeout=30).run()
    open_saved(app, original.run_id)
    assert any('no saved model to resume' in item.value for item in app.warning)
    assert not any(button.label == 'Resume experiment' for button in app.button)
    click(app, 'Restart as new run')
    snapshot = learning_session(tmp_path).wait(20)
    app.run()
    assert not app.exception
    assert not app.error
    assert snapshot.run.run_id != original.run_id
    assert snapshot.run.config == original.config
    assert metadata.read_bytes() == unchanged
    assert len(repository.list_runs()) == 2


def test_missing_model_shows_recovery_message_and_intact_metadata_without_stale_result(tmp_path, monkeypatch):
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(tmp_path))
    repository = RunRepository(tmp_path)
    run = run_comparison(LearningConfig(grid_size=5, total_budget=10), repository.save_checkpoint,
                         pause_requested=lambda: True)
    app = AppTest.from_file(APP, default_timeout=30).run()
    open_saved(app, run.run_id)
    assert len(app.get('plotly_chart')) == 5
    missing = tmp_path / run.run_id / 'iteration-000/adaptive-model.json'
    missing.unlink()
    click(app, 'Open selected run')
    assert not app.exception
    assert any('Missing artifact: adaptive-model.json' in item.value for item in app.error)
    assert any('Restore the complete original run folder' in item.value for item in app.info)
    assert len(app.get('plotly_chart')) == 0
    assert not any(button.label == 'Resume experiment' for button in app.button)
    assert any('Intact configuration and date' in item.value for item in app.markdown)
    assert (tmp_path / run.run_id / 'run.json').exists()


def test_changed_settings_create_another_run_without_rewriting_saved_history(tmp_path, monkeypatch):
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(tmp_path))
    repository = RunRepository(tmp_path)
    original = run_comparison(LearningConfig(seed=1, grid_size=5, total_budget=10), repository.save_checkpoint)
    folder = tmp_path / original.run_id
    unchanged = {path: path.read_bytes() for path in folder.rglob('*') if path.is_file()}
    app = AppTest.from_file(APP, default_timeout=30).run()
    open_saved(app, original.run_id)
    app.radio(key='view').set_value('Experiment').run()
    app.number_input[0].set_value(2).run()
    click(app, 'Run experiment')
    completed = learning_session(tmp_path).wait(20)
    app.run()
    assert not app.exception
    assert completed.error is None
    assert completed.run.config.seed == 2
    assert completed.run.run_id != original.run_id
    assert len(repository.list_runs()) == 2
    assert {path: path.read_bytes() for path in folder.rglob('*') if path.is_file()} == unchanged
