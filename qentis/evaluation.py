"""Held-out numerical labels live here, outside acquisition's interface."""

from dataclasses import dataclass
from hashlib import sha256

import numpy as np

from .config import LearningConfig, SolverSettings
from .physics import reference_point
from .surrogate import ModelError, coordinates


@dataclass(frozen=True)
class EvaluationSet:
    points: np.ndarray
    labels: np.ndarray
    identity: str

    def to_dict(self) -> dict:
        return {"points": self.points.tolist(), "labels": self.labels.tolist(), "identity": self.identity,
                "protocol": "interior400-v1", "seed": 20261018}

    @classmethod
    def from_dict(cls, data: dict) -> "EvaluationSet":
        points, labels = coordinates(data["points"]), np.asarray(data["labels"], dtype=float)
        identity = sha256(points.tobytes() + labels.tobytes()).hexdigest()
        if points.shape != (400, 2) or labels.shape != (400,) or not np.isfinite(labels).all() or identity != data["identity"]:
            raise ModelError("Invalid held-out reference artifact.")
        return cls(points, labels, identity)


def prepare_evaluation(config: LearningConfig, solver: SolverSettings, progress=lambda *args: None) -> EvaluationSet:
    points = np.random.default_rng(20261018).uniform(0.005, 0.995, size=(400, 2))
    points *= [config.gamma_max, config.time_max]
    labels = []
    for index, (gamma, time) in enumerate(points):
        labels.append(reference_point(float(gamma), float(time), solver))
        if (index + 1) % 50 == 0:
            progress("preparing reference", index + 1, 400)
    values = np.asarray(labels)
    return EvaluationSet(points, values, sha256(points.tobytes() + values.tobytes()).hexdigest())


def evaluate(mean, std, reference: EvaluationSet) -> dict:
    mean, std = np.asarray(mean), np.asarray(std)
    if (mean.shape != reference.labels.shape or std.shape != mean.shape
            or not np.isfinite(mean).all() or not np.isfinite(std).all() or np.any(std < 0)):
        raise ModelError("Evaluation requires finite means and nonnegative estimated uncertainty.")
    errors = mean - reference.labels
    return {"rmse": float(np.sqrt(np.mean(errors**2))), "mae": float(np.mean(np.abs(errors))),
            "max_absolute_error": float(np.max(np.abs(errors))),
            "outside_physical_fraction": float(np.mean((mean < -1) | (mean > 1))),
            "interval_coverage": float(np.mean(np.abs(errors) <= 1.96 * std)),
            "mean_interval_width": float(np.mean(2 * 1.96 * std))}
