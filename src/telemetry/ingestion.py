"""Telemetry Ingestion Interface providing buffering, windowing, and feature extraction preparation.
Designed to be plug-and-play with future OpenTelemetry collector streams.
"""
from typing import List, Dict, Any, Optional
from collections import defaultdict
from src.telemetry.models import TelemetryPoint, LogEntry, TraceSpan

class TelemetryIngestionBuffer:
    """In-memory telemetry buffer supporting sliding window queries and feature aggregation."""

    def __init__(self, max_points_per_metric: int = 5000):
        self.max_points = max_points_per_metric
        # Map: (service, metric_name) -> List[TelemetryPoint]
        self._metrics: Dict[str, List[TelemetryPoint]] = defaultdict(list)
        self._logs: List[LogEntry] = []
        self._traces: List[TraceSpan] = []

    def ingest_metric(self, point: TelemetryPoint) -> None:
        """Ingest a single metric point."""
        key = f"{point.service}:{point.metric}"
        buf = self._metrics[key]
        buf.append(point)
        if len(buf) > self.max_points:
            self._metrics[key] = buf[-self.max_points:]

    def ingest_log(self, log: LogEntry) -> None:
        """Ingest a single structured log entry."""
        self._logs.append(log)
        if len(self._logs) > self.max_points * 2:
            self._logs = self._logs[-self.max_points * 2:]

    def ingest_trace(self, span: TraceSpan) -> None:
        """Ingest a distributed trace span."""
        self._traces.append(span)
        if len(self._traces) > self.max_points * 2:
            self._traces = self._traces[-self.max_points * 2:]

    def ingest_batch(
        self,
        metrics: List[TelemetryPoint],
        logs: Optional[List[LogEntry]] = None,
        traces: Optional[List[TraceSpan]] = None
    ) -> None:
        """Ingest a batch of metrics, logs, and traces."""
        for m in metrics:
            self.ingest_metric(m)
        if logs:
            for l in logs:
                self.ingest_log(l)
        if traces:
            for t in traces:
                self.ingest_trace(t)

    def get_metric_history(
        self,
        service: str,
        metric: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[TelemetryPoint]:
        """Query time series data for a specific metric within a time range."""
        key = f"{service}:{metric}"
        points = self._metrics.get(key, [])
        if start_time is None and end_time is None:
            return list(points)
        return [
            p for p in points
            if (start_time is None or p.timestamp >= start_time) and (end_time is None or p.timestamp <= end_time)
        ]

    def get_logs_in_window(
        self,
        service: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        min_level: Optional[str] = None
    ) -> List[LogEntry]:
        """Query logs filtered by window and service."""
        level_hierarchy = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "CRITICAL": 4}
        min_val = level_hierarchy.get(min_level, 0) if min_level else 0

        filtered = []
        for l in self._logs:
            if service and l.service != service:
                continue
            if start_time and l.timestamp < start_time:
                continue
            if end_time and l.timestamp > end_time:
                continue
            if level_hierarchy.get(l.level.value, 0) < min_val:
                continue
            filtered.append(l)
        return filtered

    def get_traces_in_window(
        self,
        service: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        only_errors: bool = False
    ) -> List[TraceSpan]:
        """Query trace spans filtered by service and time window."""
        filtered = []
        for s in self._traces:
            if service and s.service != service:
                continue
            if start_time and s.start_time < start_time:
                continue
            if end_time and s.start_time > end_time:
                continue
            if only_errors and not s.has_error and s.status_code < 400:
                continue
            filtered.append(s)
        return filtered

    def clear(self):
        """Clear all buffers."""
        self._metrics.clear()
        self._logs.clear()
        self._traces.clear()
