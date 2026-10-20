"""Paired, transactional learning steps. Selection never receives evaluation labels."""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

import numpy as np
from threadpoolctl import threadpool_limits

from .config import ExperimentConfig, LearningConfig, PHYSICAL_CONVENTION, SolverSettings
from .evaluation import EvaluationSet, evaluate, prepare_evaluation
from .physics import Trajectory, reference_point, simulate, validate_reference
from .provenance import capture_provenance
from .surrogate import FIT_POLICY, ModelError, SurrogateModel, fit_model

STRATEGIES = ("adaptive", "random")


def candidate_pool(config: LearningConfig) -> np.ndarray:
    gamma, time = np.meshgrid(np.linspace(0, config.gamma_max, config.grid_size),
                              np.linspace(0, config.time_max, config.grid_size), indexing="ij")
    return np.column_stack((gamma.ravel(), time.ravel()))


def select_adaptive(model: SurrogateModel, candidates: np.ndarray, acquired_ids) -> tuple[int, float]:
    """Only model uncertainty, coordinates and training IDs; stable first-max tie rule."""
    available = np.setdiff1d(np.arange(len(candidates)), acquired_ids)
    if not len(available):
        raise ModelError("No unqueried candidate remains.")
    _, std = model.predict(candidates[available])
    offset = int(np.argmax(std))
    return int(available[offset]), float(std[offset])


def select_random(candidates: np.ndarray, acquired_ids, rng: np.random.Generator) -> int:
    available = np.setdiff1d(np.arange(len(candidates)), acquired_ids)
    if not len(available):
        raise ModelError("No unqueried candidate remains.")
    return int(rng.choice(available))


@dataclass(frozen=True)
class Observation:
    candidate_id: int
    value: float


@dataclass(frozen=True)
class StrategyState:
    observations: tuple[Observation, ...]
    model: SurrogateModel
    candidate_mean: np.ndarray
    candidate_std: np.ndarray
    evaluation_mean: np.ndarray
    evaluation_std: np.ndarray
    metrics: dict
    selection: dict | None
    next_selection: dict | None

    @property
    def ids(self) -> list[int]:
        return [item.candidate_id for item in self.observations]


@dataclass(frozen=True)
class IterationCheckpoint:
    iteration: int
    strategies: dict[str, StrategyState]
    counts: dict
    elapsed_seconds: float
    random_state: dict
    created_at: str


@dataclass
class LearningRun:
    metadata: dict
    candidates: np.ndarray
    evaluation: EvaluationSet | None
    trajectory: Trajectory | None
    checkpoints: list[IterationCheckpoint] = field(default_factory=list)
    visualization_slices: tuple[Trajectory, ...] = ()

    @property
    def run_id(self) -> str:
        return self.metadata["run_id"]

    @property
    def config(self) -> LearningConfig:
        return LearningConfig(**self.metadata["configuration"])

    @property
    def latest(self) -> IterationCheckpoint:
        return self.checkpoints[-1]


class LearningFailure(RuntimeError):
    def __init__(self, message: str, run: LearningRun | None = None):
        super().__init__(message)
        self.run = run


def _state(observations, selection, run: LearningRun, seed: int) -> StrategyState:
    ids = [item.candidate_id for item in observations]
    model = fit_model(run.candidates[ids], [item.value for item in observations],
                      [run.config.gamma_max, run.config.time_max], seed)
    means, stds = model.predict(run.candidates)
    eval_mean, eval_std = model.predict(run.evaluation.points)
    next_selection = None
    if len(ids) < run.config.total_budget:
        point_id, score = select_adaptive(model, run.candidates, ids)
        next_selection = {"candidate_id": point_id, "score": score}
    return StrategyState(tuple(observations), model, means, stds, eval_mean, eval_std,
                         evaluate(eval_mean, eval_std, run.evaluation), selection, next_selection)


def new_comparison(config: LearningConfig, solver: SolverSettings = SolverSettings()) -> LearningRun:
    """Immutable intent exists before expensive preparation or a first checkpoint."""
    streams = np.random.SeedSequence(config.seed).spawn(3)
    seeds = {name: int(stream.generate_state(1)[0])
             for name, stream in zip(("initial", "random", "model"), streams)}
    metadata = {"schema_version": 3, "kind": "qubit-learning", "run_id": f"qentis-{uuid4().hex}",
                "created_at": datetime.now(timezone.utc).isoformat(), "status": "preparing",
                "configuration": config.to_dict(), "physical_convention": dict(PHYSICAL_CONVENTION),
                "solver": solver.to_dict(), "fit_policy": FIT_POLICY, "seed_streams": seeds,
                "protocol": "single-seed-paired-v1", "color_ranges": {"uncertainty": [0, 1], "error": [0, 1]},
                "provenance": capture_provenance()}
    return LearningRun(metadata, candidate_pool(config), None, None)


def _acquire(run, point_id, cache, counts):
    if point_id in cache:
        counts["cache_hits"] += 1
    else:
        gamma, time = map(float, run.candidates[point_id])
        cache[point_id] = reference_point(gamma, time, SolverSettings(**run.metadata["solver"]))
        counts["training_solver_calls" if time > 0 else "zero_time_labels"] += 1
    return Observation(point_id, cache[point_id])


def advance_comparison(run: LearningRun, commit, progress=lambda *args: None) -> LearningRun:
    """Advance exactly one complete pair; resume only uses confirmed checkpoint state."""
    clock = perf_counter()
    run.metadata.pop("failure", None)
    try:
        config, seeds = run.config, run.metadata["seed_streams"]
        with threadpool_limits(limits=1):
            if not run.checkpoints:
                solver = SolverSettings(**run.metadata["solver"])
                progress("validating", 0, 1)
                validation = validate_reference(solver)
                evaluation = prepare_evaluation(config, solver, progress)
                progress("preparing visualization", 0, config.grid_size)
                slices = tuple(simulate(ExperimentConfig(float(gamma), config.time_max, 201), solver)
                               for gamma in np.linspace(0, config.gamma_max, config.grid_size))
                run.evaluation, run.visualization_slices = evaluation, slices
                run.trajectory = slices[config.grid_size // 2]
                run.metadata.update(reference_validation=validation, evaluation_identity=evaluation.identity)
                counts = {"validation_solver_calls": validation["numerical_solver_calls"],
                          "evaluation_solver_calls": 400, "visualization_solver_calls": config.grid_size,
                          "training_solver_calls": 0, "zero_time_labels": 0, "cache_hits": 0,
                          "acquired_labels": {"adaptive": 8, "random": 8}}
                rng = np.random.default_rng(seeds["random"])
                initial_ids = np.random.default_rng(seeds["initial"]).choice(len(run.candidates), 8, replace=False)
                progress("initial observations", 0, 8)
                cache = {}
                initial = tuple(_acquire(run, int(i), cache, counts) for i in initial_ids)
                counts["cache_hits"] += 8
                progress("initial fit", 8, config.total_budget)
                state = _state(initial, None, run, seeds["model"])
                states, iteration, elapsed = {name: state for name in STRATEGIES}, 0, 0.
            else:
                previous = run.latest
                if previous.iteration + 8 >= config.total_budget:
                    raise ValueError("This comparison is already complete.")
                iteration, elapsed = previous.iteration + 1, previous.elapsed_seconds
                counts = deepcopy(previous.counts)
                rng = np.random.default_rng()
                rng.bit_generator.state = deepcopy(previous.random_state)
                cache = {item.candidate_id: item.value for state in previous.strategies.values()
                         for item in state.observations}
                states = {}
                for name in STRATEGIES:
                    state = previous.strategies[name]
                    progress(f"selecting · {name}", iteration + 7, config.total_budget)
                    if name == "adaptive":
                        point_id, score = select_adaptive(state.model, run.candidates, state.ids)
                    else:
                        point_id, score = select_random(run.candidates, state.ids, rng), None
                    progress(f"simulating · {name}", iteration + 7, config.total_budget)
                    observation = _acquire(run, point_id, cache, counts)
                    progress(f"fitting and evaluating · {name}", iteration + 7, config.total_budget)
                    states[name] = _state((*state.observations, observation),
                                          {"candidate_id": point_id, "score": score}, run, seeds["model"])
                counts["acquired_labels"] = {name: iteration + 8 for name in STRATEGIES}
            checkpoint = IterationCheckpoint(iteration, states, deepcopy(counts), elapsed + perf_counter() - clock,
                                              deepcopy(rng.bit_generator.state), datetime.now(timezone.utc).isoformat())
            run.checkpoints.append(checkpoint)
            run.metadata["status"] = "complete" if iteration + 8 == config.total_budget else "running"
            progress("checkpointing", iteration + 8, config.total_budget)
            try:
                commit(run)
            except Exception:
                run.checkpoints.pop()
                raise
        progress("paired step saved", iteration + 8, config.total_budget)
        return run
    except Exception as exc:
        run.metadata["status"] = "failed"
        run.metadata["failure"] = {"message": str(exc), "latest_complete_iteration":
                                    run.latest.iteration if run.checkpoints else None}
        raise LearningFailure(f"Comparison stopped: {exc}", run) from exc


def resume_comparison(run: LearningRun, commit, progress=lambda *args: None,
                      pause_requested=lambda: False) -> LearningRun:
    """A pause is observed only at a complete paired checkpoint boundary."""
    if not run.checkpoints:
        raise LearningFailure("No complete checkpoint exists. Restart as a new run.", run)
    while run.latest.iteration + 8 < run.config.total_budget:
        if pause_requested():
            run.metadata["status"] = "paused"
            commit(run)
            return run
        advance_comparison(run, commit, progress)
    return run


def run_comparison(config: LearningConfig, commit, progress=lambda *args: None,
                   solver: SolverSettings = SolverSettings(), pause_requested=lambda: False) -> LearningRun:
    """Convenience synchronous workflow, using the same recoverable one-pair engine."""
    run = new_comparison(config, solver)
    advance_comparison(run, commit, progress)
    return resume_comparison(run, commit, progress, pause_requested)
