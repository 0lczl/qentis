"""Public scientific-input boundary; no dashboard or solver is required."""

from dataclasses import FrozenInstanceError

import pytest

from qentis.config import ConfigurationError, ExperimentConfig


@pytest.mark.parametrize("settings", [
    {"gamma": -0.1}, {"gamma": 2.1}, {"gamma": float("nan")},
    {"gamma": float("inf")}, {"gamma": True}, {"gamma": "1"},
    {"max_time": 0}, {"max_time": -1}, {"max_time": 5.1},
    {"max_time": float("nan")}, {"max_time": float("inf")},
    {"time_samples": 1}, {"time_samples": 1002},
    {"time_samples": 201.0}, {"time_samples": True},
])
def test_invalid_settings_are_rejected_before_computation(settings):
    with pytest.raises(ConfigurationError):
        ExperimentConfig(**settings)


def test_an_existing_configuration_cannot_be_edited_in_place():
    config = ExperimentConfig()
    with pytest.raises(FrozenInstanceError):
        config.gamma = 0.0
    assert config.to_dict() == {"gamma": 1.0, "max_time": 5.0, "time_samples": 201}
