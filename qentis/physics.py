"""Numerical Lindblad reference and independent analytical/physical checks.

Only `validate_trajectory` uses the analytical expression. Acquired reference
values and visualization states always come from numerical evolution (apart
from the exact initial condition at time zero).
"""

from dataclasses import asdict, dataclass
import warnings

import numpy as np

# Qentis uses Plotly. QuTiP's optional matplotlib plotting is never requested;
# suppress only its import-time notice, never numerical/integration warnings.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message=r"matplotlib not found: Graphics will not work\.",
                            category=UserWarning, module="qutip")
    import qutip as qt

from .config import ConfigurationError, ExperimentConfig, SolverSettings, finite_number

ANALYTICAL_TOLERANCE = 1e-6
PHYSICAL_TOLERANCE = 1e-8


class SimulationError(RuntimeError):
    """The numerical reference could not be computed."""


class ReferenceValidationError(SimulationError):
    """Unvalidated output must not become presentation data."""


@dataclass(frozen=True)
class ValidationReport:
    passed: bool
    max_analytical_error: float
    max_trace_error: float
    max_hermiticity_error: float
    min_eigenvalue: float
    max_bloch_radius: float
    max_population_error: float
    max_transverse_error: float
    analytical_tolerance: float = ANALYTICAL_TOLERANCE
    physical_tolerance: float = PHYSICAL_TOLERANCE

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Trajectory:
    gamma: float
    times: np.ndarray
    states: np.ndarray
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Own read-only buffers: callers cannot accidentally mutate a saved result.
        for name, dtype in (("times", float), ("states", complex)):
            value = np.array(getattr(self, name), dtype=dtype, copy=True)
            value.setflags(write=False)
            object.__setattr__(self, name, value)

    @property
    def bloch(self) -> np.ndarray:
        return np.column_stack((2 * self.states[:, 0, 1].real,
                                -2 * self.states[:, 0, 1].imag,
                                (self.states[:, 0, 0] - self.states[:, 1, 1]).real))

    @property
    def populations(self) -> np.ndarray:
        return np.diagonal(self.states, axis1=1, axis2=2).real

    @property
    def purity(self) -> np.ndarray:
        return np.einsum("nij,nji->n", self.states, self.states).real


def evolve(gamma: float, times: np.ndarray, solver: SolverSettings = SolverSettings()) -> Trajectory:
    """Evolve |+><+| on a finite, increasing grid beginning at zero.

    This lower-level interface also supports a single time-zero state. Grid
    limits for interactive runs belong to ExperimentConfig, not to the physics.
    """
    gamma = finite_number(gamma, "Dephasing rate")
    if gamma < 0:
        raise ConfigurationError("Dephasing rate cannot be negative.")
    times = np.asarray(times, dtype=float)
    if (times.ndim != 1 or not 1 <= len(times) <= 1001 or not np.isfinite(times).all()
            or times[0] != 0 or np.any(np.diff(times) <= 0)):
        raise ConfigurationError("Times must be a finite, increasing grid starting at zero (1–1001 samples).")
    initial = qt.ket2dm((qt.basis(2, 0) + qt.basis(2, 1)).unit())
    if len(times) == 1:
        return Trajectory(gamma, times, initial.full()[None, :, :])
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            solution = qt.mesolve(
                0 * qt.sigmaz(), initial, times,
                c_ops=[np.sqrt(gamma / 2) * qt.sigmaz()],
                options={**solver.to_dict(), "store_states": True, "progress_bar": ""},
            )
        states = np.asarray([state.full() for state in solution.states])
    except Exception as exc:
        raise SimulationError(f"QuTiP could not evolve the qubit: {exc}") from exc
    if states.shape != (len(times), 2, 2) or not np.isfinite(states).all():
        raise SimulationError("The solver returned incomplete or non-finite density matrices.")
    return Trajectory(gamma, times, states, tuple(str(item.message) for item in caught))


def simulate(config: ExperimentConfig, solver: SolverSettings = SolverSettings()) -> Trajectory:
    return evolve(config.gamma, np.linspace(0, config.max_time, config.time_samples), solver)


def reference_point(gamma: float, time: float, solver: SolverSettings = SolverSettings()) -> float:
    """One requested numerical label. A trajectory confers no extra training labels."""
    time = finite_number(time, "Time")
    if time < 0:
        raise ConfigurationError("Time cannot be negative.")
    result = evolve(gamma, np.array([0.0]) if time == 0 else np.array([0.0, time]), solver)
    require_valid(result)
    return float(result.bloch[-1, 0])


def validate_trajectory(trajectory: Trajectory) -> ValidationReport:
    states, times = trajectory.states, trajectory.times
    if (times.ndim != 1 or len(times) == 0 or times[0] != 0
            or np.any(np.diff(times) <= 0) or states.shape != (len(times), 2, 2)
            or not np.isfinite(states).all() or not np.isfinite(times).all()
            or not np.isfinite(trajectory.gamma) or trajectory.gamma < 0):
        raise ReferenceValidationError("The reference contains invalid or non-finite state data.")
    bloch = trajectory.bloch
    hermitian = (states + states.conj().transpose(0, 2, 1)) / 2
    metrics = {
        "max_analytical_error": float(np.max(np.abs(bloch[:, 0] - np.exp(-trajectory.gamma * times)))),
        "max_trace_error": float(np.max(np.abs(np.trace(states, axis1=1, axis2=2) - 1))),
        "max_hermiticity_error": float(np.max(np.abs(states - states.conj().transpose(0, 2, 1)))),
        "min_eigenvalue": float(np.min(np.linalg.eigvalsh(hermitian))),
        "max_bloch_radius": float(np.max(np.linalg.norm(bloch, axis=1))),
        "max_population_error": float(np.max(np.abs(np.diagonal(states, axis1=1, axis2=2) - 0.5))),
        "max_transverse_error": float(np.max(np.abs(bloch[:, 1:]))),
    }
    passed = (
        metrics["max_analytical_error"] <= ANALYTICAL_TOLERANCE
        and metrics["max_trace_error"] <= PHYSICAL_TOLERANCE
        and metrics["max_hermiticity_error"] <= PHYSICAL_TOLERANCE
        and metrics["min_eigenvalue"] >= -PHYSICAL_TOLERANCE
        and metrics["max_bloch_radius"] <= 1 + PHYSICAL_TOLERANCE
        and metrics["max_population_error"] <= PHYSICAL_TOLERANCE
        and metrics["max_transverse_error"] <= PHYSICAL_TOLERANCE
    )
    return ValidationReport(passed, **metrics)


def require_valid(trajectory: Trajectory) -> ValidationReport:
    report = validate_trajectory(trajectory)
    if not report.passed:
        raise ReferenceValidationError(
            "Numerical reference validation failed. Presentation-data preparation is blocked. "
            f"Diagnostics: {report.to_dict()}"
        )
    return report


def validate_reference(solver: SolverSettings = SolverSettings()) -> dict:
    """Independent boundary/interior gate, run before saving presentation data."""
    times = np.array([0.0, 1e-8, 0.1, 1.0, 5.0])
    cases = [
        {"gamma": gamma, "times": times.tolist(), "report": require_valid(evolve(gamma, times, solver)).to_dict()}
        for gamma in (0.0, 1.0, 2.0)
    ]
    zero = require_valid(evolve(1.0, np.array([0.0]), solver))
    return {"protocol": "dephasing-reference-v1", "passed": True, "cases": cases,
            "zero_time": zero.to_dict(), "numerical_solver_calls": len(cases)}
