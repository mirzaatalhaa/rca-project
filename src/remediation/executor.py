"""Remediation Executor for executing policy-checked actions on the simulator."""
import time
from typing import Dict, Any, Optional
from src.telemetry.simulator import TelemetrySimulator
from src.remediation.policy import RemediationPolicyEngine

class RemediationExecutor:
    """Executes safe remediation operations against the simulated target."""

    def __init__(self, policy_engine: Optional[RemediationPolicyEngine] = None):
        self.policy = policy_engine or RemediationPolicyEngine()

    def execute(self, action: str, service: str, simulator: TelemetrySimulator) -> Dict[str, Any]:
        """Validate against policy and execute on simulator."""
        start_t = time.time()
        
        # 1. Policy validation
        allowed, policy_msg = self.policy.validate(action, service)
        if not allowed:
            duration_ms = (time.time() - start_t) * 1000.0
            return {
                "action": action,
                "status": "REJECTED",
                "policy_check": "FAILED",
                "duration_ms": round(duration_ms, 2),
                "error": policy_msg,
                "effective": False,
            }

        # 2. Record execution for loop protection
        self.policy.record_execution(service, action)

        # 3. Execute in simulator
        effective = simulator.apply_remediation(action)
        duration_ms = (time.time() - start_t) * 1000.0

        return {
            "action": action,
            "status": "SUCCESS",
            "policy_check": "PASSED",
            "duration_ms": round(duration_ms, 2),
            "effective": effective,
            "error": None,
        }
