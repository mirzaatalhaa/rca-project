"""Deterministic, reproducible telemetry simulator supporting 6 operational scenarios

and dynamic state transitions for self-healing verification.
"""
import time
import random
import uuid
from typing import Dict, List, Tuple, Optional
from src.telemetry.models import TelemetryPoint, LogEntry, TraceSpan, GroundTruth, LogLevel

SCENARIOS = {
    "NORMAL_OPERATION": "normal_operation",
    "HIGH_LATENCY": "high_latency",
    "ELEVATED_HTTP_ERROR_RATE": "elevated_http_error_rate",
    "DATABASE_CONNECTION_FAILURE": "database_connection_failure",
    "CPU_MEMORY_PRESSURE": "cpu_memory_pressure",
    "CASCADING_FAILURE": "cascading_failure",
}

class TelemetrySimulator:
    """Generates synthetic metrics, logs, and traces for testing and evaluation."""

    def __init__(self, seed: int = 42, service_name: str = "flight-api"):
        self.seed = seed
        self.rng = random.Random(seed)
        self.service_name = service_name
        self.state = {
            "fault_active": False,
            "scenario": SCENARIOS["NORMAL_OPERATION"],
            "mitigation_applied": False,
            "mitigation_action": None,
            "repaired_at": None,
            "injected_at": None,
        }

    def reset(self):
        """Reset the simulator state."""
        self.rng = random.Random(self.seed)
        self.state = {
            "fault_active": False,
            "scenario": SCENARIOS["NORMAL_OPERATION"],
            "mitigation_applied": False,
            "mitigation_action": None,
            "repaired_at": None,
            "injected_at": None,
        }

    def inject_fault(self, scenario: str):
        """Activate a simulated failure scenario."""
        if scenario not in SCENARIOS.values():
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(SCENARIOS.values())}")
        self.state["scenario"] = scenario
        self.state["fault_active"] = (scenario != SCENARIOS["NORMAL_OPERATION"])
        self.state["mitigation_applied"] = False
        self.state["mitigation_action"] = None
        self.state["injected_at"] = time.time()

    def apply_remediation(self, action: str) -> bool:
        """Apply a simulated remediation action and determine if it restores system health."""
        expected_actions = {
            SCENARIOS["HIGH_LATENCY"]: ["reduce_simulated_load", "rollback_configuration", "restart_service"],
            SCENARIOS["ELEVATED_HTTP_ERROR_RATE"]: ["restart_service", "rollback_configuration"],
            SCENARIOS["DATABASE_CONNECTION_FAILURE"]: ["reset_database_connection_pool", "restart_service"],
            SCENARIOS["CPU_MEMORY_PRESSURE"]: ["clear_memory_leak", "restart_service"],
            SCENARIOS["CASCADING_FAILURE"]: ["clear_memory_leak", "restart_service", "reset_database_connection_pool"],
        }

        current_scenario = self.state["scenario"]
        self.state["mitigation_action"] = action
        self.state["mitigation_applied"] = True

        valid_actions = expected_actions.get(current_scenario, [])
        if action in valid_actions:
            self.state["fault_active"] = False
            self.state["repaired_at"] = time.time()
            return True
        else:
            # Action was safe but ineffective for this specific root cause
            return False

    def generate_point_in_time(self, timestamp: float) -> Tuple[List[TelemetryPoint], List[LogEntry], List[TraceSpan]]:
        """Generate a single time slice of telemetry (metrics, logs, traces) based on current state."""
        fault = self.state["fault_active"]
        scen = self.state["scenario"]

        metrics: List[TelemetryPoint] = []
        logs: List[LogEntry] = []
        traces: List[TraceSpan] = []

        # Baseline normal values
        latency = self.rng.gauss(95.0, 12.0)
        req_rate = max(10.0, self.rng.gauss(150.0, 15.0))
        error_rate = max(0.0, self.rng.gauss(0.5, 0.2))
        cpu = max(5.0, min(95.0, self.rng.gauss(25.0, 4.0)))
        memory = max(10.0, min(95.0, self.rng.gauss(38.0, 3.0)))
        db_conn = max(2.0, min(100.0, self.rng.gauss(14.0, 2.5)))

        trace_id = str(uuid.UUID(int=self.rng.getrandbits(128)))
        span_id = str(uuid.UUID(int=self.rng.getrandbits(64)))[:16]

        if not fault:
            # Healthy logs & traces
            if self.rng.random() < 0.2:
                logs.append(LogEntry(
                    timestamp=timestamp,
                    service=self.service_name,
                    level=LogLevel.INFO,
                    message="GET /api/v1/flights status=200 response_time_ms=85",
                    trace_id=trace_id,
                    span_id=span_id,
                ))
            traces.append(TraceSpan(
                trace_id=trace_id,
                span_id=span_id,
                service=self.service_name,
                operation="GET /api/v1/flights",
                start_time=timestamp,
                duration_ms=latency,
                status_code=200,
                has_error=False,
            ))
        else:
            # Fault-induced anomalies
            if scen == SCENARIOS["HIGH_LATENCY"]:
                latency = self.rng.gauss(3400.0, 350.0)
                cpu += 15.0
                logs.append(LogEntry(
                    timestamp=timestamp,
                    service=self.service_name,
                    level=LogLevel.WARN,
                    message=f"Slow query detected on database: query duration {int(latency*0.8)}ms exceeding 1000ms threshold",
                    trace_id=trace_id,
                    span_id=span_id,
                ))
                traces.append(TraceSpan(
                    trace_id=trace_id,
                    span_id=span_id,
                    service=self.service_name,
                    operation="GET /api/v1/flights/live",
                    start_time=timestamp,
                    duration_ms=latency,
                    status_code=200,
                    has_error=False,
                ))

            elif scen == SCENARIOS["ELEVATED_HTTP_ERROR_RATE"]:
                error_rate = self.rng.gauss(58.0, 6.0)
                latency = self.rng.gauss(420.0, 45.0)
                logs.append(LogEntry(
                    timestamp=timestamp,
                    service=self.service_name,
                    level=LogLevel.ERROR,
                    message="Internal Server Error: Unhandled exception in FlightController.processStream - null pointer in radar feeder",
                    trace_id=trace_id,
                    span_id=span_id,
                ))
                traces.append(TraceSpan(
                    trace_id=trace_id,
                    span_id=span_id,
                    service=self.service_name,
                    operation="POST /api/v1/telemetry/feed",
                    start_time=timestamp,
                    duration_ms=latency,
                    status_code=500,
                    has_error=True,
                ))

            elif scen == SCENARIOS["DATABASE_CONNECTION_FAILURE"]:
                db_conn = 100.0
                error_rate = self.rng.gauss(82.0, 5.0)
                latency = self.rng.gauss(2100.0, 200.0)
                logs.append(LogEntry(
                    timestamp=timestamp,
                    service=self.service_name,
                    level=LogLevel.CRITICAL,
                    message="Database connection pool exhausted: Active connections 100/100. Timeout waiting for free connection after 5000ms",
                    trace_id=trace_id,
                    span_id=span_id,
                ))
                traces.append(TraceSpan(
                    trace_id=trace_id,
                    span_id=span_id,
                    service=self.service_name,
                    operation="GET /api/v1/airports",
                    start_time=timestamp,
                    duration_ms=latency,
                    status_code=503,
                    has_error=True,
                ))

            elif scen == SCENARIOS["CPU_MEMORY_PRESSURE"]:
                cpu = min(99.0, self.rng.gauss(96.0, 2.0))
                memory = min(98.5, self.rng.gauss(94.0, 2.5))
                latency = self.rng.gauss(1850.0, 180.0)
                logs.append(LogEntry(
                    timestamp=timestamp,
                    service=self.service_name,
                    level=LogLevel.WARN,
                    message="High resource pressure: CPU at 96% and memory heap consumption at 94%. Major garbage collection pause observed (620ms)",
                    trace_id=trace_id,
                    span_id=span_id,
                ))
                traces.append(TraceSpan(
                    trace_id=trace_id,
                    span_id=span_id,
                    service=self.service_name,
                    operation="GET /api/v1/radar/snapshot",
                    start_time=timestamp,
                    duration_ms=latency,
                    status_code=200,
                    has_error=False,
                ))

            elif scen == SCENARIOS["CASCADING_FAILURE"]:
                memory = min(99.0, self.rng.gauss(97.0, 1.5))
                cpu = min(98.0, self.rng.gauss(92.0, 3.0))
                db_conn = 100.0
                error_rate = self.rng.gauss(68.0, 7.0)
                latency = self.rng.gauss(4200.0, 400.0)
                logs.append(LogEntry(
                    timestamp=timestamp,
                    service=self.service_name,
                    level=LogLevel.CRITICAL,
                    message="Cascading failure detected: OutOfMemoryError impending. Connection pool timeout and thread starvation occurring across flight-api",
                    trace_id=trace_id,
                    span_id=span_id,
                ))
                traces.append(TraceSpan(
                    trace_id=trace_id,
                    span_id=span_id,
                    service=self.service_name,
                    operation="GET /api/v1/flights/realtime",
                    start_time=timestamp,
                    duration_ms=latency,
                    status_code=500,
                    has_error=True,
                ))

        # Assemble metric data points
        metrics.extend([
            TelemetryPoint(timestamp=timestamp, service=self.service_name, metric="request_latency_ms", value=round(latency, 2), unit="ms"),
            TelemetryPoint(timestamp=timestamp, service=self.service_name, metric="request_rate_rps", value=round(req_rate, 2), unit="rps"),
            TelemetryPoint(timestamp=timestamp, service=self.service_name, metric="http_error_rate_pct", value=round(max(0.0, error_rate), 2), unit="%"),
            TelemetryPoint(timestamp=timestamp, service=self.service_name, metric="cpu_utilization_pct", value=round(cpu, 2), unit="%"),
            TelemetryPoint(timestamp=timestamp, service=self.service_name, metric="memory_utilization_pct", value=round(memory, 2), unit="%"),
            TelemetryPoint(timestamp=timestamp, service=self.service_name, metric="db_connection_usage", value=round(db_conn, 2), unit="connections"),
        ])

        return metrics, logs, traces

    def generate_time_series(
        self,
        normal_steps: int = 30,
        incident_steps: int = 15,
        step_seconds: float = 10.0,
        scenario: str = SCENARIOS["HIGH_LATENCY"]
    ) -> Tuple[List[TelemetryPoint], List[LogEntry], List[TraceSpan], GroundTruth]:
        """Generate a complete reproducible time-series sequence with pre-incident baseline and incident window.
        Returns: (metrics, logs, traces, ground_truth)
        """
        self.reset()
        base_time = 1700000000.0
        all_metrics: List[TelemetryPoint] = []
        all_logs: List[LogEntry] = []
        all_traces: List[TraceSpan] = []

        # 1. Generate normal baseline
        for i in range(normal_steps):
            t = base_time + (i * step_seconds)
            m, l, tr = self.generate_point_in_time(t)
            all_metrics.extend(m)
            all_logs.extend(l)
            all_traces.extend(tr)

        # 2. Inject fault if not normal
        injected_timestamp = base_time + (normal_steps * step_seconds)
        if scenario != SCENARIOS["NORMAL_OPERATION"]:
            self.inject_fault(scenario)

        # 3. Generate incident steps
        for i in range(incident_steps):
            t = injected_timestamp + (i * step_seconds)
            m, l, tr = self.generate_point_in_time(t)
            all_metrics.extend(m)
            all_logs.extend(l)
            all_traces.extend(tr)

        ground_truth = self.get_ground_truth(scenario, injected_timestamp)
        return all_metrics, all_logs, all_traces, ground_truth

    def get_ground_truth(self, scenario: str, injected_timestamp: float) -> GroundTruth:
        """Create the ground-truth metadata label for experimental evaluation (kept separate from diagnosis)."""
        gt_map = {
            SCENARIOS["NORMAL_OPERATION"]: GroundTruth(
                scenario_id="SCEN-00",
                scenario_name="Normal Baseline Operation",
                fault_injected="none",
                affected_service=self.service_name,
                primary_root_cause="nominal",
                expected_remediation="none",
                symptoms=[],
                injected_at=injected_timestamp,
            ),
            SCENARIOS["HIGH_LATENCY"]: GroundTruth(
                scenario_id="SCEN-01",
                scenario_name="Unindexed Query Induced High Latency",
                fault_injected="slow_queries_unindexed_join",
                affected_service=self.service_name,
                primary_root_cause="Unindexed database query causing severe backend thread backlog and high response latency",
                expected_remediation="reduce_simulated_load",
                symptoms=["request_latency_ms spike", "slow query database logs"],
                injected_at=injected_timestamp,
            ),
            SCENARIOS["ELEVATED_HTTP_ERROR_RATE"]: GroundTruth(
                scenario_id="SCEN-02",
                scenario_name="Application Crash Exception Error Spike",
                fault_injected="null_pointer_radar_feeder_bug",
                affected_service=self.service_name,
                primary_root_cause="Null pointer exception in FlightController causing 500 Internal Server Errors",
                expected_remediation="restart_service",
                symptoms=["http_error_rate_pct spike", "HTTP 500 error logs"],
                injected_at=injected_timestamp,
            ),
            SCENARIOS["DATABASE_CONNECTION_FAILURE"]: GroundTruth(
                scenario_id="SCEN-03",
                scenario_name="Database Connection Pool Starvation",
                fault_injected="connection_leak_unclosed_sessions",
                affected_service=self.service_name,
                primary_root_cause="Database connection pool exhaustion due to unclosed sessions reaching maximum limit of 100",
                expected_remediation="reset_database_connection_pool",
                symptoms=["db_connection_usage 100%", "503 Service Unavailable", "Pool timeout logs"],
                injected_at=injected_timestamp,
            ),
            SCENARIOS["CPU_MEMORY_PRESSURE"]: GroundTruth(
                scenario_id="SCEN-04",
                scenario_name="Memory Leak and Garbage Collection Thrashing",
                fault_injected="in_memory_cache_memory_leak",
                affected_service=self.service_name,
                primary_root_cause="Memory leak in radar telemetry cache driving memory utilization above 90% and causing CPU thrashing",
                expected_remediation="clear_memory_leak",
                symptoms=["memory_utilization_pct > 90%", "cpu_utilization_pct > 90%", "GC pauses"],
                injected_at=injected_timestamp,
            ),
            SCENARIOS["CASCADING_FAILURE"]: GroundTruth(
                scenario_id="SCEN-05",
                scenario_name="Cascading Resource Starvation Across System",
                fault_injected="unbounded_telemetry_buffer_cascade",
                affected_service=self.service_name,
                primary_root_cause="Severe cascading failure triggered by memory exhaustion propagating to DB pool starvation and HTTP 500 errors",
                expected_remediation="restart_service",
                symptoms=["high latency", "high error rate", "exhausted DB pool", "memory > 95%"],
                injected_at=injected_timestamp,
            ),
        }
        return gt_map.get(scenario, gt_map[SCENARIOS["NORMAL_OPERATION"]])
