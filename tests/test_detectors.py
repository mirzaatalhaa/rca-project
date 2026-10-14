"""Tests for Anomaly Detection (Statistical Z-Score and Isolation Forest)."""
import pytest
from src.telemetry.simulator import TelemetrySimulator, SCENARIOS
from src.detection.statistical import StatisticalZScoreDetector
from src.detection.ml_detector import IsolationForestDetector
from src.telemetry.models import TelemetryPoint

def test_statistical_detector_nominal_and_anomaly():
    sim = TelemetrySimulator(seed=123)
    train_points = []
    for i in range(30):
        pts, _, _ = sim.generate_point_in_time(100.0 + i)
        train_points.extend(pts)

    detector = StatisticalZScoreDetector(threshold_z=3.0)
    detector.fit(train_points)

    # Normal point should not flag
    normal_pt = TelemetryPoint(timestamp=200.0, service="flight-api", metric="request_latency_ms", value=95.0)
    assert detector.detect(normal_pt) is None

    # Extreme latency spike should flag
    spike_pt = TelemetryPoint(timestamp=201.0, service="flight-api", metric="request_latency_ms", value=3500.0)
    evt = detector.detect(spike_pt)
    assert evt is not None
    assert evt.is_anomaly is True
    assert evt.severity in ("high", "critical")
    assert evt.score > 3.0

def test_isolation_forest_multivariate_detection():
    sim = TelemetrySimulator(seed=456)
    train_points = []
    for i in range(40):
        pts, _, _ = sim.generate_point_in_time(100.0 + i)
        train_points.extend(pts)

    ml_det = IsolationForestDetector(contamination=0.08)
    ml_det.fit(train_points)

    # Inlier observation
    norm_pts, _, _ = sim.generate_point_in_time(300.0)
    evt_norm = ml_det.detect_multivariate(norm_pts)
    assert evt_norm is None

    # Anomaly observation with fault
    sim.inject_fault(SCENARIOS["HIGH_LATENCY"])
    anom_pts, _, _ = sim.generate_point_in_time(400.0)
    evt_anom = ml_det.detect_multivariate(anom_pts)
    assert evt_anom is not None
    assert evt_anom.is_anomaly is True
    assert evt_anom.detector_type == "isolation_forest"
