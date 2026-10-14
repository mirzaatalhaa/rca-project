"""Tests for Remediation Policy Engine and Executor."""
from src.remediation.policy import RemediationPolicyEngine
from src.remediation.executor import RemediationExecutor
from src.telemetry.simulator import TelemetrySimulator, SCENARIOS

def test_policy_allowlist_and_safety():
    policy = RemediationPolicyEngine(max_retries=2, loop_cooldown_seconds=60.0)

    # Valid allowed action
    valid, msg = policy.validate("restart_service", "flight-api")
    assert valid is True
    assert "PASSED" in msg

    # Disallowed action
    invalid, msg = policy.validate("drop_all_tables", "flight-api")
    assert invalid is False
    assert "REJECTED" in msg

    # Command injection attempt
    malicious, msg = policy.validate("restart_service; rm -rf /", "flight-api")
    assert malicious is False
    assert "SECURITY ALERT" in msg

def test_flapping_and_loop_protection():
    policy = RemediationPolicyEngine(max_retries=2, loop_cooldown_seconds=60.0)

    # First attempt
    v1, _ = policy.validate("restart_service", "flight-api")
    assert v1 is True
    policy.record_execution("flight-api", "restart_service")

    # Second attempt
    v2, _ = policy.validate("restart_service", "flight-api")
    assert v2 is True
    policy.record_execution("flight-api", "restart_service")

    # Third attempt should be blocked by loop protection
    v3, msg = policy.validate("restart_service", "flight-api")
    assert v3 is False
    assert "Repeated remediation loop detected" in msg

def test_executor_execution():
    sim = TelemetrySimulator()
    sim.inject_fault(SCENARIOS["CPU_MEMORY_PRESSURE"])
    executor = RemediationExecutor()

    res = executor.execute("clear_memory_leak", "flight-api", sim)
    assert res["status"] == "SUCCESS"
    assert res["effective"] is True
    assert sim.state["fault_active"] is False
