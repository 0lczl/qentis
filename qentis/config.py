"""Versioned, immutable scientific inputs for the simulation phase."""

from dataclasses import asdict, dataclass
import math
from numbers import Real


class ConfigurationError(ValueError):
    """An experiment cannot start with these inputs."""


def finite_number(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ConfigurationError(f"{label} must be a finite number.")
    return float(value)


@dataclass(frozen=True)
class ExperimentConfig:
    gamma: float = 1.0
    max_time: float = 5.0
    time_samples: int = 201

    def __post_init__(self) -> None:
        gamma = finite_number(self.gamma, "Dephasing rate")
        time = finite_number(self.max_time, "Maximum time")
        if not 0 <= gamma <= 2:
            raise ConfigurationError("Dephasing rate must be between 0 and 2 inverse time units.")
        if not 0 < time <= 5:
            raise ConfigurationError("Maximum time must be greater than 0 and at most 5 time units.")
        if type(self.time_samples) is not int or not 2 <= self.time_samples <= 1001:
            raise ConfigurationError("Time samples must be an integer between 2 and 1001.")
        object.__setattr__(self, "gamma", gamma)
        object.__setattr__(self, "max_time", time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SolverSettings:
    atol: float = 1e-10
    rtol: float = 1e-8
    method: str = "adams"
    nsteps: int = 10000
    normalize_output: bool = False

    def __post_init__(self) -> None:
        if finite_number(self.atol, "Absolute tolerance") <= 0:
            raise ConfigurationError("Absolute tolerance must be positive.")
        if finite_number(self.rtol, "Relative tolerance") <= 0:
            raise ConfigurationError("Relative tolerance must be positive.")
        if self.method != "adams" or type(self.nsteps) is not int or self.nsteps < 1:
            raise ConfigurationError("The supported solver is adams with a positive integer step limit.")
        if self.normalize_output is not False:
            raise ConfigurationError("Output normalization must remain off for physical validation.")

    def to_dict(self) -> dict:
        return asdict(self)


PHYSICAL_CONVENTION = {
    "system": "one qubit, pure dephasing",
    "initial_state": "|+> = (|0> + |1>) / sqrt(2)",
    "hbar": 1,
    "hamiltonian": "H = 0",
    "collapse_operator": "L = sqrt(gamma / 2) * sigma_z",
    "master_equation": "d rho / dt = (gamma / 2) * (sigma_z rho sigma_z - rho)",
    "observable": "x = 2 Re(rho_01)",
    "time_unit": "dimensionless time unit",
    "gamma_unit": "inverse dimensionless time unit",
}


@dataclass(frozen=True)
class LearningConfig:
    """Short comparison defaults; changed protocols are exploratory."""
    seed: int = 0
    gamma_max: float = 2.0
    time_max: float = 5.0
    grid_size: int = 21
    total_budget: int = 24

    def __post_init__(self) -> None:
        for name, cap in (("gamma_max", 2), ("time_max", 5)):
            value = finite_number(getattr(self, name), name)
            if not 0 < value <= cap:
                raise ConfigurationError(f"{name} must be positive and at most {cap}.")
            object.__setattr__(self, name, value)
        if type(self.seed) is not int or not 0 <= self.seed <= 2**32 - 1:
            raise ConfigurationError("Seed must be an integer from 0 to 4294967295.")
        if type(self.grid_size) is not int or not 3 <= self.grid_size <= 31:
            raise ConfigurationError("Candidate grid must have 3–31 points on each axis.")
        if type(self.total_budget) is not int or not 8 <= self.total_budget <= min(64, self.grid_size**2):
            raise ConfigurationError("Total budget must be 8–64 and fit the unique candidate pool.")

    @property
    def preset(self) -> bool:
        return (self.gamma_max, self.time_max, self.grid_size, self.total_budget) == (2., 5., 21, 24)

    def to_dict(self) -> dict:
        return asdict(self)
