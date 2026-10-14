"""Telemetry models and types for metrics, logs, traces, and ground truth."""
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class TelemetryPoint(BaseModel):
    timestamp: float = Field(..., description="Epoch timestamp in seconds")
    service: str = Field(..., description="Service identifier, e.g., 'flight-api', 'auth-service'")
    metric: str = Field(..., description="Metric name, e.g. 'request_latency_ms'")
    value: float = Field(..., description="Observed numeric value")
    unit: str = Field(default="", description="Unit of measurement, e.g. 'ms', '%', 'rps'")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class LogEntry(BaseModel):
    timestamp: float = Field(..., description="Epoch timestamp in seconds")
    service: str = Field(...)
    level: LogLevel = Field(...)
    message: str = Field(...)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service: str
    operation: str
    start_time: float
    duration_ms: float
    status_code: int = 200
    has_error: bool = False
    attributes: Dict[str, Any] = Field(default_factory=dict)

class GroundTruth(BaseModel):
    scenario_id: str
    scenario_name: str
    fault_injected: str
    affected_service: str
    primary_root_cause: str
    expected_remediation: str
    symptoms: List[str]
    injected_at: float
