"""Fixed Gaussian-process policy and non-executable, portable model state."""

from dataclasses import dataclass
import warnings

import numpy as np
from scipy.linalg import solve_triangular
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern


class ModelError(RuntimeError):
    """A model cannot produce trustworthy finite estimates."""


FIT_POLICY = {"version": "matern52-scaled-v1", "kernel": "constant * Matern(nu=2.5, ARD)",
              "initial_amplitude": 1., "amplitude_bounds": [0.001, 1000.],
              "initial_length_scales": [0.3, 0.3], "length_scale_bounds": [0.02, 10.],
              "alpha": 1e-10, "normalize_y": False, "optimizer": "fmin_l_bfgs_b",
              "optimizer_restarts": 0, "scaling": "divide coordinates by domain upper bounds"}


def coordinates(points) -> np.ndarray:
    values = np.asarray(points, dtype=float)
    if values.ndim != 2 or values.shape[1] != 2 or not np.isfinite(values).all():
        raise ModelError("Coordinates must be a finite array of (gamma, time) pairs.")
    return values


@dataclass(frozen=True)
class SurrogateModel:
    scale: np.ndarray
    training_scaled: np.ndarray
    dual: np.ndarray
    cholesky: np.ndarray
    amplitude: float
    length_scales: np.ndarray
    warnings: tuple[str, ...] = ()

    def predict(self, points) -> tuple[np.ndarray, np.ndarray]:
        inputs = coordinates(points) / self.scale
        kernel = ConstantKernel(self.amplitude) * Matern(self.length_scales, nu=2.5)
        cross = kernel(inputs, self.training_scaled)
        mean = cross @ self.dual
        solved = solve_triangular(self.cholesky, cross.T, lower=True, check_finite=False)
        variance = kernel.diag(inputs) - np.einsum("ij,ij->j", solved, solved)
        if not np.isfinite(mean).all() or not np.isfinite(variance).all() or np.min(variance, initial=0) < -1e-7:
            raise ModelError("Gaussian-process prediction has non-finite or unstable covariance.")
        return mean, np.sqrt(np.maximum(variance, 0))

    def to_dict(self) -> dict:
        return {"schema_version": 1, "policy": FIT_POLICY, "scale": self.scale.tolist(),
                "training_scaled": self.training_scaled.tolist(), "dual": self.dual.tolist(),
                "cholesky": self.cholesky.tolist(), "amplitude": self.amplitude,
                "length_scales": self.length_scales.tolist(), "warnings": list(self.warnings)}

    @classmethod
    def from_dict(cls, data: dict) -> "SurrogateModel":
        if data["schema_version"] != 1 or data["policy"] != FIT_POLICY:
            raise ModelError("Unsupported saved model policy or schema.")
        model = cls(*(np.asarray(data[key], dtype=float) for key in
                      ("scale", "training_scaled", "dual", "cholesky")),
                    float(data["amplitude"]), np.asarray(data["length_scales"], dtype=float),
                    tuple(data["warnings"]))
        count = len(model.dual)
        arrays = (model.scale, model.training_scaled, model.dual, model.cholesky, model.length_scales)
        if (not 8 <= count <= 64 or model.scale.shape != (2,) or np.any(model.scale <= 0)
                or model.training_scaled.shape != (count, 2) or model.dual.shape != (count,)
                or model.cholesky.shape != (count, count) or model.length_scales.shape != (2,)
                or any(not np.isfinite(a).all() for a in arrays)
                or not np.isfinite(model.amplitude) or model.amplitude <= 0
                or np.any(model.length_scales <= 0) or np.any(np.diag(model.cholesky) <= 1e-12)
                or not np.array_equal(model.cholesky, np.tril(model.cholesky))):
            raise ModelError("Invalid saved Gaussian-process state.")
        return model


def fit_model(points, labels, scale, seed: int) -> SurrogateModel:
    points = coordinates(points)
    labels, scale = np.asarray(labels, dtype=float), np.asarray(scale, dtype=float)
    if (labels.shape != (len(points),) or not 8 <= len(points) <= 64
            or scale.shape != (2,) or np.any(scale <= 0) or not np.isfinite(scale).all()
            or not np.isfinite(labels).all()):
        raise ModelError("Training needs 8–64 finite numerical observations and positive scaling.")
    gp = GaussianProcessRegressor(
        kernel=ConstantKernel(1., (0.001, 1000.)) * Matern([0.3, 0.3], (0.02, 10.), nu=2.5),
        alpha=1e-10, normalize_y=False, n_restarts_optimizer=0, random_state=seed)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            gp.fit(points / scale, labels)
        model = SurrogateModel(scale.copy(), (points / scale).copy(), gp.alpha_.copy(), gp.L_.copy(),
                               float(gp.kernel_.k1.constant_value), gp.kernel_.k2.length_scale.copy(),
                               tuple(str(item.message) for item in caught))
        # Validate persisted state through the same public artifact interface used at reload.
        model = SurrogateModel.from_dict(model.to_dict())
        model.predict(points)
        return model
    except ModelError:
        raise
    except Exception as exc:
        raise ModelError(f"Gaussian-process fit failed: {exc}") from exc
