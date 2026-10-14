"""Data models for comprehensive persistent Incident Reports."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class IncidentReport(BaseModel):
    incident_id: str
    timestamp: float
    iso_timestamp: str
    scenario_name: str
    affected_service: str
    anomaly_detection: Dict[str, Any]
    supporting_evidence: List[str]
    rca_diagnosis: Dict[str, Any]
    selected_action: str
    action_execution_result: Dict[str, Any]
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    recovery_verification: Dict[str, Any]
    ground_truth_comparison: Optional[Dict[str, Any]] = None
    execution_time_seconds: float = 0.0
