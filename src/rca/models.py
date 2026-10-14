"""Data models for Root Cause Analysis (RCA)."""
from typing import List, Optional
from pydantic import BaseModel, Field

class RCADiagnosis(BaseModel):
    incident_id: str = Field(..., description="Unique incident identifier")
    affected_service: str = Field(..., description="Service diagnosed")
    detected_symptoms: List[str] = Field(..., description="Key observed symptoms across metrics/logs/traces")
    probable_root_cause: str = Field(..., description="Primary diagnosed root cause")
    supporting_evidence: List[str] = Field(..., description="Bullet points of concrete evidence from logs/traces/metrics")
    alternative_hypotheses: List[str] = Field(default_factory=list, description="Other plausible causes considered")
    severity: str = Field(..., description="Assessed incident severity: low, medium, high, critical")
    confidence: float = Field(..., description="Confidence level between 0.0 and 1.0")
    recommended_remediation: str = Field(..., description="Selected action from allowed remediation catalog")
    remediation_rationale: str = Field(..., description="Explanation of why this action safely addresses the root cause")
    llm_provider: str = Field(default="mock", description="Provider used: e.g. mock, openai, gemini")
    is_mock_result: bool = Field(default=False, description="Flag indicating if result is mock/rule-based rather than LLM")
