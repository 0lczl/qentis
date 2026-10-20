"""One real simulation run; called explicitly, never by dashboard inspection."""

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from .config import ExperimentConfig, PHYSICAL_CONVENTION, SolverSettings
from .physics import Trajectory, require_valid, simulate, validate_reference
from .provenance import capture_provenance

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Run:
    metadata: dict
    trajectory: Trajectory

    @property
    def run_id(self) -> str:
        return self.metadata["run_id"]

    @property
    def config(self) -> ExperimentConfig:
        return ExperimentConfig(**self.metadata["configuration"])


def create_run(config: ExperimentConfig, solver: SolverSettings = SolverSettings()) -> Run:
    started = datetime.now(timezone.utc).isoformat()
    clock = perf_counter()
    reference_validation = validate_reference(solver)
    trajectory = simulate(config, solver)
    report = require_valid(trajectory)
    completed = datetime.now(timezone.utc).isoformat()
    return Run({
        "schema_version": SCHEMA_VERSION,
        "kind": "qubit-simulation",
        "run_id": f"qentis-{uuid4().hex}",
        "created_at": started,
        "completed_at": completed,
        "status": "complete",
        "configuration": config.to_dict(),
        "physical_convention": dict(PHYSICAL_CONVENTION),
        "solver": {"library": "qutip", "function": "mesolve", "settings": solver.to_dict(),
                   "store_states": True},
        "reference_validation": reference_validation,
        "trajectory_validation": report.to_dict(),
        "numerical_warnings": list(trajectory.warnings),
        "counts": {"validation_solver_calls": reference_validation["numerical_solver_calls"],
                   "visualization_solver_calls": 1, "acquired_labels": 0,
                   "evaluation_solver_calls": 0, "cache_hits": 0},
        "timing": {"reference_and_validation_seconds": perf_counter() - clock},
        "provenance": capture_provenance(),
    }, trajectory)
