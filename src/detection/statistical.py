"""Statistical Z-score Baseline Anomaly Detector.
Extends and productionizes the baseline detector from anomaly-detection/src/detector.py
with per-metric baselining, configurable thresholds, and structured event emission.
"""
import statistics
from typing import Dict, List, Optional
from collections import defaultdict
from src.telemetry.models import TelemetryPoint
from src.detection.models import AnomalyEvent
from src.detection.base import BaseAnomalyDetector
from src.config import settings

class StatisticalZScoreDetector(BaseAnomalyDetector):
    """Z-Score anomaly detector learning mean and variance per (service, metric)."""

    def __init__(self, threshold_z: Optional[float] = None):
        self.threshold_z = threshold_z if threshold_z is not None else settings.STATISTICAL_Z_THRESHOLD
        # Key: (service, metric) -> {"mean": float, "std": float, "count": int}
        self.baselines: Dict[str, Dict[str, float]] = {}

    def _key(self, service: str, metric: str) -> str:
        return f"{service}:{metric}"

    def fit(self, training_data: List[TelemetryPoint]) -> None:
        """Calculate mean and standard deviation for each service and metric."""
        grouped: Dict[str, List[float]] = defaultdict(list)
        for p in training_data:
            grouped[self._key(p.service, p.metric)].append(p.value)

        for key, values in grouped.items():
            if len(values) >= 2:
                m = statistics.mean(values)
                s = statistics.stdev(values)
                self.baselines[key] = {
                    "mean": m,
                    "std": s if s > 1e-4 else 1.0,
                    "count": len(values)
                }
            elif len(values) == 1:
                self.baselines[key] = {
                    "mean": values[0],
                    "std": 1.0,
                    "count": 1
                }

    def detect(self, point: TelemetryPoint) -> Optional[AnomalyEvent]:
        """Compute Z-score against learned baseline."""
        key = self._key(point.service, point.metric)
        stats = self.baselines.get(key)

        if not stats:
            # Not enough historical baseline to assert an anomaly safely
            return None

        mean = stats["mean"]
        std = stats["std"]
        z_score = abs(point.value - mean) / std

        if z_score > self.threshold_z:
            confidence = min(0.99, max(0.50, 1.0 - (1.0 / z_score)))
            
            if z_score >= 6.0:
                severity = "critical"
            elif z_score >= 4.0:
                severity = "high"
            elif z_score >= 3.0:
                severity = "medium"
            else:
                severity = "low"

            return AnomalyEvent(
                is_anomaly=True,
                service=point.service,
                metric=point.metric,
                timestamp=point.timestamp,
                observed_value=point.value,
                baseline_value=round(mean, 2),
                score=round(z_score, 2),
                confidence=round(confidence, 2),
                severity=severity,
                detector_type="statistical_z_score",
                reason=(
                    f"{point.metric} value {point.value:.2f}{point.unit} deviated significantly "
                    f"by {z_score:.2f} standard deviations from baseline mean {mean:.2f}{point.unit}."
                ),
                metadata={
                    "z_score": round(z_score, 2),
                    "threshold_z": self.threshold_z,
                    "baseline_std": round(std, 2)
                }
            )

        return None
