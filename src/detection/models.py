"""Anomaly detection data schemas."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class AnomalyEvent(BaseModel):
    is_anomaly: bool = True
    service: str = Field(..., description="Service affected")
    metric: str = Field(..., description="Primary anomalous metric")
    timestamp: float = Field(..., description="Timestamp of the anomalous observation")
    observed_value: float = Field(..., description="Observed value during anomaly")
    baseline_value: float = Field(..., description="Learned normal baseline mean")
    score: float = Field(..., description="Anomaly score (Z-score or normalized distance)")
    confidence: float = Field(default=0.85, description="Confidence score between 0.0 and 1.0")
    severity: str = Field(..., description="Severity level: low, medium, high, critical")
    detector_type: str = Field(..., description="Detector used: statistical_z_score or isolation_forest")
    reason: str = Field(..., description="Human-readable explanation of why this was flagged")
    metadata: Dict[str, Any] = Field(default_factory=dict)
