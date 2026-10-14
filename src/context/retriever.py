"""Context Retrieval Component.
Extracts high-signal, explainable evidence surrounding an anomaly event
from telemetry buffer (metrics, logs, traces) for LLM root cause analysis.
"""
import uuid
from typing import List, Dict, Any, Optional
from src.detection.models import AnomalyEvent
from src.telemetry.ingestion import TelemetryIngestionBuffer
from src.context.models import IncidentContext
from src.config import settings

class ContextRetriever:
    """Retrieves and ranks relevant diagnostic context for an anomaly."""

    def __init__(self, buffer: TelemetryIngestionBuffer, window_seconds: float = 60.0):
        self.buffer = buffer
        self.window_seconds = window_seconds

    def retrieve_context(
        self,
        anomaly_event: AnomalyEvent,
        recent_events: Optional[List[str]] = None
    ) -> IncidentContext:
        """Select relevant evidence around the incident timestamp."""
        ts = anomaly_event.timestamp
        window_start = max(0.0, ts - self.window_seconds)
        window_end = ts + 5.0
        service = anomaly_event.service
        incident_id = f"INC-{str(uuid.uuid4())[:8].upper()}"

        # 1. Summarize metrics across the window
        metrics_summary: Dict[str, Dict[str, Any]] = {}
        for m in settings.TRACKED_METRICS:
            pts = self.buffer.get_metric_history(service, m, start_time=window_start, end_time=window_end)
            if pts:
                vals = [p.value for p in pts]
                metrics_summary[m] = {
                    "latest": round(vals[-1], 2),
                    "baseline": anomaly_event.baseline_value if m == anomaly_event.metric else round(sum(vals)/len(vals), 2),
                    "mean_in_window": round(sum(vals) / len(vals), 2),
                    "max_in_window": round(max(vals), 2),
                    "min_in_window": round(min(vals), 2),
                    "count": len(vals),
                }

        # 2. Retrieve and rank relevant logs
        raw_logs = self.buffer.get_logs_in_window(service=service, start_time=window_start, end_time=window_end)
        scored_logs = []
        for l in raw_logs:
            # Score based on log level and keyword relevance
            score = 0
            lvl = l.level.value
            if lvl in ("CRITICAL", "FATAL"):
                score += 50
            elif lvl == "ERROR":
                score += 35
            elif lvl == "WARN":
                score += 15

            # Keyword relevance
            msg_lower = l.message.lower()
            keywords = ["exception", "timeout", "exhausted", "slow query", "crash", "starvation", "heap", "null pointer", "refused"]
            for kw in keywords:
                if kw in msg_lower:
                    score += 20

            # Time proximity bonus (closer to incident timestamp = higher)
            time_diff = abs(ts - l.timestamp)
            proximity_score = max(0.0, 10.0 - (time_diff / 5.0))
            score += proximity_score

            if score > 0:
                scored_logs.append({
                    "timestamp": round(l.timestamp, 1),
                    "level": lvl,
                    "message": l.message,
                    "relevance_score": round(score, 1),
                    "trace_id": l.trace_id
                })

        # Sort logs by relevance descending
        scored_logs.sort(key=lambda x: x["relevance_score"], reverse=True)

        # 3. Retrieve and filter traces
        raw_traces = self.buffer.get_traces_in_window(service=service, start_time=window_start, end_time=window_end)
        failed_or_slow_traces = []
        for tr in raw_traces:
            is_slow = tr.duration_ms > 1000.0
            if tr.has_error or tr.status_code >= 400 or is_slow:
                failed_or_slow_traces.append({
                    "trace_id": tr.trace_id,
                    "operation": tr.operation,
                    "duration_ms": round(tr.duration_ms, 1),
                    "status_code": tr.status_code,
                    "has_error": tr.has_error,
                    "start_time": round(tr.start_time, 1)
                })

        # Sort traces by error priority and duration
        failed_or_slow_traces.sort(key=lambda x: (x["has_error"], x["duration_ms"]), reverse=True)

        return IncidentContext(
            incident_id=incident_id,
            timestamp=ts,
            affected_service=service,
            anomaly_event=anomaly_event,
            window_start=window_start,
            window_end=window_end,
            metrics_summary=metrics_summary,
            relevant_logs=scored_logs[:10],
            failed_traces=failed_or_slow_traces[:8],
            recent_deployments_or_events=recent_events or []
        )
