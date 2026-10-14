"""Base class for anomaly detectors."""
from abc import ABC, abstractmethod
from typing import List, Optional
from src.telemetry.models import TelemetryPoint
from src.detection.models import AnomalyEvent

class BaseAnomalyDetector(ABC):
    """Abstract interface for all anomaly detectors."""

    @abstractmethod
    def fit(self, training_data: List[TelemetryPoint]) -> None:
        """Fit detector on historical normal baseline telemetry."""
        pass

    @abstractmethod
    def detect(self, point: TelemetryPoint) -> Optional[AnomalyEvent]:
        """Evaluate a single telemetry point and return AnomalyEvent if anomalous, else None."""
        pass

    def batch_detect(self, points: List[TelemetryPoint]) -> List[AnomalyEvent]:
        """Detect anomalies across a list of points."""
        anomalies = []
        for p in points:
            evt = self.detect(p)
            if evt is not None and evt.is_anomaly:
                anomalies.append(evt)
        return anomalies
