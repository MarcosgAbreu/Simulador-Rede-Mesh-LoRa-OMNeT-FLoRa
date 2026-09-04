import pytest

from lora_mesh.config import SimulationConfig, ValidationError


def test_defaults_match_requested_scenario():
    config = SimulationConfig()
    assert config.area_m == 1000.0
    assert config.activation_min_s == 0.0
    assert config.activation_max_s == 3600.0
    assert config.simulation_time_s == 14400.0


def test_activation_interval_cannot_exceed_simulation_time():
    with pytest.raises(ValidationError):
        SimulationConfig(activation_max_s=500.0, simulation_time_s=100.0)


def test_same_seed_produces_same_serialized_configuration():
    first = SimulationConfig(seed=17).to_dict()
    second = SimulationConfig(seed=17).to_dict()
    assert first == second
