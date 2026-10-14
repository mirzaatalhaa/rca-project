"""Tests for Context Retrieval."""
from src.telemetry.simulator import TelemetrySimulator, SCENARIOS
from src.telemetry.ingestion import TelemetryIngestionBuffer
from src.detection.models import AnomalyEvent
from src.context.retriever import ContextRetriever

def test_context_retriever_ranking_and_filtering():
    sim = TelemetrySimulator(seed=789)
    buffer = TelemetryIngestionBuffer()

    # Ingest historical telemetry
    for i in range(10):
        pts, logs, traces = sim.generate_point_in_time(100.0 + i * 5.0)
        buffer.ingest_batch(pts, logs, traces)

    # Inject fault and ingest abnormal telemetry
    sim.inject_fault(SCENARIOS["DATABASE_CONNECTION_FAILURE"])
    anom_pts, anom_logs, anom_traces = sim.generate_point_in_time(200.0)
    buffer.ingest_batch(anom_pts, anom_logs, anom_traces)

    evt = AnomalyEvent(
        is_anomaly=True,
        service="flight-api",
        metric="db_connection_usage",
        timestamp=200.0,
        observed_value=100.0,
        baseline_value=14.0,
        score=25.0,
        severity="critical",
        detector_type="statistical_z_score",
        reason="DB connection usage reached 100%"
    )

    retriever = ContextRetriever(buffer, window_seconds=60.0)
    context = retriever.retrieve_context(evt)

    assert context.affected_service == "flight-api"
    assert len(context.relevant_logs) > 0
    # Top log should mention database or connection
    top_log_msg = context.relevant_logs[0]["message"].lower()
    assert "database" in top_log_msg or "connection" in top_log_msg or "exhausted" in top_log_msg
    assert len(context.failed_traces) > 0
