"""Presenter behavior through Streamlit's supported app-testing interface."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from qentis.repository import RunRepository

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv("QENTIS_RUNS_DIR", str(tmp_path / "results"))
    return AppTest.from_file(APP, default_timeout=20).run(), RunRepository(tmp_path / "results")


def click(app, label):
    if label == "Run simulation" and not any(button.label == label for button in app.button):
        app.radio(key="experiment_type").set_value("Qubit simulation").run()
    next(button for button in app.button if button.label == label).click().run()


def test_running_the_dashboard_computes_validated_states_and_saves_them(dashboard):
    app, repository = dashboard
    assert not app.exception
    click(app, "Run simulation")
    assert not app.exception
    assert not app.error
    assert not app.warning
    summaries = repository.list_runs()
    assert len(summaries) == 1
    run = repository.load(summaries[0].run_id)
    assert run.metadata["trajectory_validation"]["passed"] is True
    assert run.metadata["counts"]["acquired_labels"] == 0
    assert len(run.trajectory.times) == 201


def test_slider_inspection_updates_both_charts_without_another_solve_or_save(dashboard, monkeypatch):
    import qutip
    app, repository = dashboard
    click(app, "Run simulation")
    summary = repository.list_runs()[0]
    run = repository.load(summary.run_id)
    def unexpected_solve(*args, **kwargs):
        raise AssertionError("Inspecting stored data must not invoke the numerical solver")
    monkeypatch.setattr(qutip, "mesolve", unexpected_solve)
    app.select_slider[0].set_value(200).run()
    assert not app.exception
    assert not app.error
    sphere, curve = [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]
    assert sphere["data"][-1]["x"][-1] == run.trajectory.bloch[-1, 0]
    assert curve["data"][-1]["x"] == [5.0]
    assert curve["data"][-1]["y"] == [run.trajectory.bloch[-1, 0]]
    assert [item.run_id for item in repository.list_runs()] == [summary.run_id]


def test_a_new_dashboard_session_reopens_a_saved_run_without_recomputing(dashboard, monkeypatch):
    import qutip
    app, repository = dashboard
    click(app, "Run simulation")
    run_id = repository.list_runs()[0].run_id
    def unexpected_solve(*args, **kwargs):
        raise AssertionError("Opening saved numerical states must not run the solver")
    monkeypatch.setattr(qutip, "mesolve", unexpected_solve)
    fresh = AppTest.from_file(APP, default_timeout=20).run()
    fresh.radio[0].set_value("Saved runs").run()
    fresh.selectbox[0].set_value(run_id).run()
    click(fresh, "Open selected run")
    assert not fresh.exception
    assert not fresh.error
    assert len(fresh.get("plotly_chart")) == 2
    assert any("Saved result" in item.value for item in fresh.markdown)
    assert [item.run_id for item in repository.list_runs()] == [run_id]


def test_a_numerical_failure_is_visible_and_preserves_the_previous_valid_result(dashboard, monkeypatch):
    import qutip
    app, repository = dashboard
    click(app, "Run simulation")
    run_id = repository.list_runs()[0].run_id
    def failed_solve(*args, **kwargs):
        raise RuntimeError("external numerical solver failed")
    monkeypatch.setattr(qutip, "mesolve", failed_solve)
    click(app, "Run simulation")
    assert not app.exception
    assert any("external numerical solver failed" in error.value for error in app.error)
    assert [item.run_id for item in repository.list_runs()] == [run_id]
    assert len(app.get("plotly_chart")) == 2


def test_a_failed_save_never_displays_a_successful_result(tmp_path, monkeypatch):
    location = tmp_path / "results"
    location.write_text("not a directory")
    monkeypatch.setenv("QENTIS_RUNS_DIR", str(location))
    app = AppTest.from_file(APP, default_timeout=20).run()
    click(app, "Run simulation")
    assert not app.exception
    assert any("not confirmed saved" in error.value for error in app.error)
    assert len(app.get("plotly_chart")) == 0


def test_the_empty_saved_library_has_a_working_route_to_experiment(dashboard):
    app, repository = dashboard
    app.radio[0].set_value("Saved runs").run()
    assert any("No saved runs yet" in message.value for message in app.info)
    click(app, "Go to Experiment")
    assert not app.exception
    assert app.radio[0].value == "Experiment"
    assert any(button.label in ("Run simulation", "Run experiment") for button in app.button)
    assert repository.list_runs() == []


def test_a_failed_reopen_does_not_show_a_stale_successful_load(dashboard):
    app, repository = dashboard
    click(app, "Run simulation")
    run_id = repository.list_runs()[0].run_id
    app.radio[0].set_value("Saved runs").run()
    click(app, "Open selected run")
    assert len(app.get("plotly_chart")) == 2
    (repository.root / run_id / "trajectory.npz").unlink()
    click(app, "Open selected run")
    assert not app.exception
    assert any("Missing artifact: trajectory.npz" in error.value for error in app.error)
    assert len(app.get("plotly_chart")) == 0
