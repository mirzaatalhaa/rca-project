"""Machine Learning Anomaly Detector using Isolation Forest.
Provides multivariate anomaly detection across correlated telemetry streams.
"""
from typing import Dict, List, Optional
import numpy as np
from src.telemetry.models import TelemetryPoint
from src.detection.models import AnomalyEvent
from src.detection.base import BaseAnomalyDetector
from src.config import settings

class IsolationForestDetector(BaseAnomalyDetector):
    """Multivariate anomaly detector based on Scikit-Learn's Isolation Forest."""

    def __init__(self, contamination: Optional[float] = None, random_state: int = 42):
        self.contamination = contamination or settings.ISOLATION_FOREST_CONTAMINATION
        self.random_state = random_state
        self.model = None
        self.metric_names: List[str] = list(settings.TRACKED_METRICS)
        self.metric_means: Dict[str, float] = {}
        self.metric_stds: Dict[str, float] = {}
        self.is_fitted = False

    def _extract_multivariate_matrix(self, points: List[TelemetryPoint]) -> np.ndarray:
        """Group telemetry points by timestamp and convert to a 2D numpy array [n_samples, n_features]."""
        by_ts: Dict[float, Dict[str, float]] = {}
        for p in points:
            if p.timestamp not in by_ts:
                by_ts[p.timestamp] = {}
            by_ts[p.timestamp][p.metric] = p.value

        rows = []
        for ts, mdict in sorted(by_ts.items()):
            row = [mdict.get(m, self.metric_means.get(m, 0.0)) for m in self.metric_names]
            rows.append(row)

        if not rows:
            return np.empty((0, len(self.metric_names)))
        return np.array(rows, dtype=np.float64)

    def fit(self, training_data: List[TelemetryPoint]) -> None:
        """Fit the Isolation Forest model on historical normal baseline telemetry."""
        from sklearn.ensemble import IsolationForest

        # Calculate baselines per metric
        by_metric: Dict[str, List[float]] = {m: [] for m in self.metric_names}
        for p in training_data:
            if p.metric in by_metric:
                by_metric[p.metric].append(p.value)

        for m, vals in by_metric.items():
            if vals:
                self.metric_means[m] = float(np.mean(vals))
                self.metric_stds[m] = float(np.std(vals)) if np.std(vals) > 1e-4 else 1.0
            else:
                self.metric_means[m] = 0.0
                self.metric_stds[m] = 1.0

        X = self._extract_multivariate_matrix(training_data)
        if len(X) < 5:
            # Not enough data for meaningful isolation forest
            return

        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100
        )
        self.model.fit(X)
        self.is_fitted = True

    def detect_multivariate(self, window_points: List[TelemetryPoint]) -> Optional[AnomalyEvent]:
        """Detect if the latest multivariate system observation is anomalous."""
        if not self.is_fitted or self.model is None:
            return None

        X = self._extract_multivariate_matrix(window_points)
        if len(X) == 0:
            return None

        # Take the most recent vector
        latest_vector = X[-1:]
        pred = self.model.predict(latest_vector)[0]  # -1 for anomaly, 1 for inlier
        raw_score = float(self.model.decision_function(latest_vector)[0])  # negative is anomaly

        # Calculate standardized deviations per feature
        diffs = []
        for i, m in enumerate(self.metric_names):
            val = latest_vector[0][i]
            mean = self.metric_means.get(m, 0.0)
            std = self.metric_stds.get(m, 1.0)
            norm_dev = abs(val - mean) / std
            diffs.append((m, val, mean, norm_dev))

        diffs.sort(key=lambda x: x[3], reverse=True)
        top_metric, top_val, top_mean, top_dev = diffs[0]

        # Flag only if Isolation Forest flags AND deviation exceeds threshold, or high deviation occurs
        is_anom = (pred == -1 and (top_dev >= 2.5 or raw_score < -0.05)) or (top_dev >= 3.5)

        if is_anom:
            # Invert score so higher = more anomalous
            anomaly_score = max(round(top_dev, 2), round(-raw_score * 10.0, 2))
            confidence = min(0.99, max(0.60, 0.5 + (anomaly_score / 10.0)))

            severity = "critical" if top_dev > 6.0 else ("high" if top_dev > 4.0 else "medium")

            latest_point = window_points[-1]
            return AnomalyEvent(
                is_anomaly=True,
                service=latest_point.service,
                metric=top_metric,
                timestamp=latest_point.timestamp,
                observed_value=top_val,
                baseline_value=round(top_mean, 2),
                score=round(anomaly_score, 2),
                confidence=round(confidence, 2),
                severity=severity,
                detector_type="isolation_forest",
                reason=(
                    f"Multivariate Isolation Forest detected out-of-distribution anomaly "
                    f"(score: {anomaly_score:.2f}). Dominant anomalous feature: {top_metric} "
                    f"({top_val:.2f} vs baseline {top_mean:.2f}, {top_dev:.1f}x std)."
                ),
                metadata={
                    "raw_decision_score": round(raw_score, 4),
                    "dominant_features": [{"metric": m, "observed": v, "std_devs": round(d, 2)} for m, v, _, d in diffs[:3]]
                }
            )

        return None

    def detect(self, point: TelemetryPoint) -> Optional[AnomalyEvent]:
        """Wrap single point into multivariate detect when possible or fallback."""
        return self.detect_multivariate([point])
