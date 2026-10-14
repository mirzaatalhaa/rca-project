"""Data models for retrieved incident context."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.detection.models import AnomalyEvent

class IncidentContext(BaseModel):
    incident_id: str
    timestamp: float
    affected_service: str
    anomaly_event: AnomalyEvent
    window_start: float
    window_end: float
    metrics_summary: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    relevant_logs: List[Dict[str, Any]] = Field(default_factory=list)
    failed_traces: List[Dict[str, Any]] = Field(default_factory=list)
    recent_deployments_or_events: List[str] = Field(default_factory=list)

    def to_formatted_prompt_context(self) -> str:
        """Render context as clean, structured, readable text for LLM consumption."""
        lines = []
        lines.append(f"### Incident Context for Service '{self.affected_service}' at timestamp {self.timestamp:.1f}")
        lines.append(f"- Primary Anomaly: {self.anomaly_event.metric} = {self.anomaly_event.observed_value} "
                     f"(Baseline: {self.anomaly_event.baseline_value}, Severity: {self.anomaly_event.severity.upper()}, Score: {self.anomaly_event.score})")
        lines.append(f"- Anomaly Explanation: {self.anomaly_event.reason}")
        
        lines.append("\n#### Recent Metrics (Observed vs Baseline):")
        for m, stats in self.metrics_summary.items():
            lines.append(f"  * {m}: latest={stats.get('latest')}, baseline={stats.get('baseline')}, mean_in_window={stats.get('mean_in_window')}")

        lines.append(f"\n#### Relevant Log Messages ({len(self.relevant_logs)} entries):")
        if not self.relevant_logs:
            lines.append("  (No abnormal log entries found)")
        else:
            for l in self.relevant_logs[:8]:  # Limit top 8 highest signal
                lines.append(f"  [{l.get('level')}] t={l.get('timestamp')}: {l.get('message')}")

        lines.append(f"\n#### Errored or High-Latency Traces ({len(self.failed_traces)} traces):")
        if not self.failed_traces:
            lines.append("  (No errored traces observed)")
        else:
            for tr in self.failed_traces[:5]:
                lines.append(f"  * Operation: {tr.get('operation')}, Duration: {tr.get('duration_ms')}ms, Status: {tr.get('status_code')}, Error: {tr.get('has_error')}")

        if self.recent_deployments_or_events:
            lines.append("\n#### Recent Operational Events:")
            for ev in self.recent_deployments_or_events:
                lines.append(f"  - {ev}")

        return "\n".join(lines)
