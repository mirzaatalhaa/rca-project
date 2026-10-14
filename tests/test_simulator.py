"""Tests for Telemetry Simulator."""
import pytest
from src.telemetry.simulator import TelemetrySimulator, SCENARIOS
from src.telemetry.models import LogLevel

def test_simulator_normal_operation():
    sim = TelemetrySimulator(seed=42)
    metrics, logs, traces = sim.generate_point_in_time(1000.0)
    
    assert len(metrics) == 6
    metrics_map = {m.metric: m.value for m in metrics}
    
    # Check nominal ranges
    assert 50.0 <= metrics_map["request_latency_ms"] <= 150.0
    assert metrics_map["http_error_rate_pct"] < 5.0
    assert metrics_map["db_connection_usage"] < 30.0
    assert len(traces) == 1
    assert not traces[0].has_error

@pytest.mark.parametrize("scenario", list(SCENARIOS.values()))
def test_all_scenarios_generate_telemetry(scenario):
    sim = TelemetrySimulator(seed=42)
    sim.inject_fault(scenario)
    metrics, logs, traces = sim.generate_point_in_time(2000.0)
    
    assert len(metrics) == 6
    gt = sim.get_ground_truth(scenario, 2000.0)
    assert gt.scenario_name is not None

def test_simulator_remediation_and_recovery():
    sim = TelemetrySimulator(seed=42)
    sim.inject_fault(SCENARIOS["DATABASE_CONNECTION_FAILURE"])
    assert sim.state["fault_active"] is True

    # Ineffective action
    assert sim.apply_remediation("clear_memory_leak") is False
    assert sim.state["fault_active"] is True

    # Effective action
    assert sim.apply_remediation("reset_database_connection_pool") is True
    assert sim.state["fault_active"] is False

    # Check generated metrics after recovery
    metrics, logs, traces = sim.generate_point_in_time(3000.0)
    metrics_map = {m.metric: m.value for m in metrics}
    assert metrics_map["db_connection_usage"] < 25.0
