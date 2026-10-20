"""Numerical behavior through the reference interface, with real QuTiP solves."""

from types import SimpleNamespace

import numpy as np
import pytest

from qentis.config import ConfigurationError, ExperimentConfig, SolverSettings
from qentis.physics import (
    ReferenceValidationError, SimulationError, Trajectory, evolve, reference_point,
    require_valid, simulate, validate_reference,
)
import qutip


@pytest.mark.parametrize("gamma", [0.0, 0.05, 0.5, 1.0, 2.0])
def test_numerical_coherence_agrees_with_the_independent_analytical_check(gamma):
    trajectory = simulate(ExperimentConfig(gamma=gamma))
    np.testing.assert_allclose(trajectory.bloch[:, 0], np.exp(-gamma * trajectory.times), rtol=0, atol=1e-6)


@pytest.mark.parametrize("gamma", [0.0, 1.0, 2.0])
def test_density_matrices_preserve_physical_invariants_and_populations(gamma):
    trajectory = simulate(ExperimentConfig(gamma=gamma))
    states = trajectory.states
    np.testing.assert_allclose(np.trace(states, axis1=1, axis2=2), 1, rtol=0, atol=1e-8)
    np.testing.assert_allclose(states, states.conj().transpose(0, 2, 1), rtol=0, atol=1e-8)
    assert np.linalg.eigvalsh(states).min() >= -1e-8
    assert np.linalg.norm(trajectory.bloch, axis=1).max() <= 1 + 1e-8
    np.testing.assert_allclose(trajectory.populations, 0.5, rtol=0, atol=1e-8)
    np.testing.assert_allclose(trajectory.bloch[:, 1:], 0, rtol=0, atol=1e-8)


def test_no_noise_preserves_the_initial_coherence_and_purity():
    trajectory = simulate(ExperimentConfig(gamma=0))
    np.testing.assert_allclose(trajectory.bloch[:, 0], 1, rtol=0, atol=1e-8)
    np.testing.assert_allclose(trajectory.purity, 1, rtol=0, atol=1e-8)


def test_zero_time_returns_the_exact_initial_density_matrix():
    trajectory = evolve(2.0, np.array([0.0]))
    np.testing.assert_allclose(trajectory.states[0], np.full((2, 2), 0.5), rtol=0, atol=1e-15)
    assert reference_point(2.0, 0.0) == pytest.approx(1.0, abs=1e-15)


def test_large_gamma_time_relaxes_to_a_mixed_state_without_changing_populations():
    trajectory = evolve(2.0, np.linspace(0, 50, 201))
    assert abs(trajectory.bloch[-1, 0]) <= 1e-6
    np.testing.assert_allclose(trajectory.populations[-1], [0.5, 0.5], rtol=0, atol=1e-8)
    assert trajectory.purity[-1] == pytest.approx(0.5, abs=1e-8)
    assert require_valid(trajectory).passed


@pytest.mark.parametrize("gamma,times", [(-1, [0, 1]), (float("nan"), [0, 1]),
    (1, []), (1, [1, 2]), (1, [0, 0]), (1, [0, -1]), (1, [0, float("inf")])])
def test_invalid_reference_coordinates_are_rejected(gamma, times):
    with pytest.raises(ConfigurationError):
        evolve(gamma, np.array(times))


def test_a_real_solver_failure_is_propagated_without_substitute_data():
    with pytest.raises(SimulationError, match="QuTiP could not evolve"):
        evolve(2.0, np.array([0.0, 5.0]), SolverSettings(nsteps=1))


def test_nonfinite_external_solver_output_is_rejected(monkeypatch):
    def broken_solver(*args, **kwargs):
        return SimpleNamespace(states=[qutip.Qobj(np.full((2, 2), np.nan)) for _ in args[2]])
    monkeypatch.setattr(qutip, "mesolve", broken_solver)
    with pytest.raises(SimulationError, match="non-finite"):
        simulate(ExperimentConfig())


def test_invalid_reference_blocks_presentation_run_preparation(monkeypatch):
    from qentis.experiment import create_run

    def stuck_solver(*args, **kwargs):
        # An external solver returning the initial state forever passes gamma=0
        # but must be caught by the nonzero-gamma gate, not replaced analytically.
        return SimpleNamespace(states=[args[1] for _ in args[2]])
    monkeypatch.setattr(qutip, "mesolve", stuck_solver)
    with pytest.raises(ReferenceValidationError, match="Presentation-data preparation is blocked"):
        create_run(ExperimentConfig())


def test_the_reference_gate_covers_noise_boundaries_and_standalone_zero_time():
    report = validate_reference()
    assert report["passed"] is True
    assert [case["gamma"] for case in report["cases"]] == [0.0, 1.0, 2.0]
    assert all(case["report"]["passed"] for case in report["cases"])
    assert report["zero_time"]["passed"] is True
