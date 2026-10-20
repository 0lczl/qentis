"""Learning and appearance through the actual Streamlit interface."""
from pathlib import Path
import json

import numpy as np
from streamlit.testing.v1 import AppTest

from qentis.repository import RunRepository

APP = Path(__file__).resolve().parents[1] / 'app.py'


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    if label == 'Run experiment':
        from qentis.runtime import learning_session
        import os
        learning_session(os.environ['QENTIS_RUNS_DIR']).wait(30)
        app.run()


def test_dashboard_completes_the_short_comparison_and_shows_real_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(tmp_path))
    app = AppTest.from_file(APP, default_timeout=30).run()
    click(app, 'Run experiment')
    assert not app.exception
    assert not app.error
    repository = RunRepository(tmp_path)
    assert len(repository.list_runs()) == 1
    run = repository.load(repository.list_runs()[0].run_id)
    assert run.latest.counts['acquired_labels'] == {'adaptive': 24, 'random': 24}
    assert len(app.get('plotly_chart')) == 5
    assert any('Single seed 0' in caption.value for caption in app.caption)
    assert any('Outside physical range' in caption.value for caption in app.caption)


def test_theme_and_revision_sliders_use_saved_models_without_solver_or_retraining(tmp_path, monkeypatch):
    import qutip
    from sklearn.gaussian_process import GaussianProcessRegressor
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(tmp_path))
    app = AppTest.from_file(APP, default_timeout=30).run()
    app.number_input[3].set_value(9).run()
    app.number_input[4].set_value(3).run()
    click(app, 'Run experiment')
    assert not app.exception
    def forbidden(*args, **kwargs):
        raise AssertionError('inspecting scientific results cannot solve or fit')
    monkeypatch.setattr(qutip, 'mesolve', forbidden)
    monkeypatch.setattr(GaussianProcessRegressor, 'fit', forbidden)
    app.toggle(key='dark_mode').set_value(False).run()
    app.select_slider[0].set_value(0).run()
    app.select_slider[1].set_value(0).run()
    app.select_slider[2].set_value(100).run()
    assert not app.exception
    assert not app.error
    charts = [json.loads(chart.proto.spec) for chart in app.get('plotly_chart')]
    assert all(chart['layout']['paper_bgcolor'] == '#ffffff' for chart in charts)
    assert any('reference x = 1.000000' in item.value for item in app.markdown)
    assert len(RunRepository(tmp_path).list_runs()) == 1


def test_fresh_dashboard_opens_a_trained_run_without_fitting_or_solver_calls(tmp_path, monkeypatch):
    import qutip
    from sklearn.gaussian_process import GaussianProcessRegressor
    from qentis.config import LearningConfig
    from qentis.learning import run_comparison
    monkeypatch.setenv('QENTIS_RUNS_DIR', str(tmp_path))
    repository = RunRepository(tmp_path)
    run = run_comparison(LearningConfig(grid_size=3, total_budget=8), repository.save_checkpoint)
    def forbidden(*args, **kwargs):
        raise AssertionError('saved models must predict without refitting or simulation')
    monkeypatch.setattr(qutip, 'mesolve', forbidden)
    monkeypatch.setattr(GaussianProcessRegressor, 'fit', forbidden)
    fresh = AppTest.from_file(APP, default_timeout=30).run()
    fresh.radio(key='view').set_value('Saved runs').run()
    fresh.selectbox[0].set_value(run.run_id).run()
    click(fresh, 'Open selected run')
    assert not fresh.exception
    assert not fresh.error
    assert len(fresh.get('plotly_chart')) == 5
    assert any('Saved result' in item.value for item in fresh.markdown)
    assert fresh.select_slider[0].value == 0
