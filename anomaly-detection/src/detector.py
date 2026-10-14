import statistics

class BaselineAnomalyDetector:
    def __init__(self, threshold_z=3.0):
        # We use a Z-score threshold. Anything beyond 3 standard deviations is an anomaly.
        self.threshold_z = threshold_z
        self.history = []
        self.mean = 0
        self.std = 0

    def fit(self, historical_values):
        """Learn what 'normal' looks like from historical data."""
        self.history = historical_values
        self.mean = statistics.mean(self.history) if self.history else 0
        self.std = statistics.stdev(self.history) if len(self.history) > 1 else 0

    def detect(self, current_data):
        """Evaluate a new telemetry point against learned baseline."""
        value = current_data['value']
        
        # Calculate Z-score: how many standard deviations away from the mean is this value?
        z_score = abs(value - self.mean) / (self.std if self.std > 0 else 1)
        
        is_anomaly = z_score > self.threshold_z
        
        if is_anomaly:
            # Calculate a pseudo-confidence score (capped at 0.99)
            confidence = min(0.99, 1.0 - (1.0 / z_score))
            return {
                "anomaly_detected": True,
                "service": current_data["service"],
                "metric": current_data["metric"],
                "severity": "high" if z_score > 5 else "medium",
                "reason": f"{current_data['metric'].capitalize()} ({value}) significantly exceeds learned normal behavior (mean: {self.mean:.2f}).",
                "timestamp": current_data["timestamp"],
                "confidence": round(confidence, 2)
            }
        
        return {"anomaly_detected": False}
