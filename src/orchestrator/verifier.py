"""Post-Action Verification Engine.
Monitors simulator health and metrics after remediation execution to verify system recovery.
"""
import time
from typing import Dict, Any, List
from src.telemetry.simulator import TelemetrySimulator
from src.detection.statistical import StatisticalZScoreDetector
from src.config import settings

class PostActionVerifier:
    """Verifies whether a remediation action restored system telemetry to nominal health."""

    def __init__(self, detector: StatisticalZScoreDetector, verification_steps: int = 5):
        self.detector = detector
        self.verification_steps = verification_steps

    def verify_recovery(
        self,
        simulator: TelemetrySimulator,
        pre_action_metrics: Dict[str, float],
        target_service: str
    ) -> Dict[str, Any]:
        """Generate post-action telemetry points and evaluate if anomalous state cleared."""
        now = time.time()
        post_metrics: Dict[str, List[float]] = {m: [] for m in settings.TRACKED_METRICS}
        has_post_errors = False

        for i in range(self.verification_steps):
            pts, logs, traces = simulator.generate_point_in_time(now + (i * 5.0))
            for p in pts:
                if p.metric in post_metrics:
                    post_metrics[p.metric].append(p.value)
            for l in logs:
                if l.level.value in ("ERROR", "CRITICAL"):
                    has_post_errors = True
            for tr in traces:
                if tr.has_error:
                    has_post_errors = True

        # Compute averages of post-action metrics
        avg_after_metrics: Dict[str, float] = {}
        for m, vals in post_metrics.items():
            avg_after_metrics[m] = round(sum(vals) / len(vals), 2) if vals else 0.0

        # Evaluate against learned detector baselines
        anomalies_remaining = []
        for m in settings.TRACKED_METRICS:
            baseline_stats = self.detector.baselines.get(f"{target_service}:{m}")
            if baseline_stats:
                mean = baseline_stats["mean"]
                std = baseline_stats["std"]
                val = avg_after_metrics.get(m, mean)
                z = abs(val - mean) / std
                if z > 2.5:
                    anomalies_remaining.append(f"{m} (Z={z:.1f})")

        # Determine recovery status
        if not simulator.state.get("fault_active", False) and len(anomalies_remaining) == 0 and not has_post_errors:
            status = "SUCCESS"
            recovered = True
            details = "All monitored service metrics normalized back within learned baseline thresholds (Z < 2.5). Zero active error logs observed."
        elif len(anomalies_remaining) > 0 or simulator.state.get("fault_active", False):
            status = "FAILED"
            recovered = False
            details = f"Telemetry remains anomalous post-remediation. Lingering deviations: {', '.join(anomalies_remaining) if anomalies_remaining else 'Fault state still asserted'}."
        else:
            status = "INCONCLUSIVE"
            recovered = False
            details = "Metrics normalized but transient error traces were still detected in verification window."

        return {
            "status": status,
            "recovered": recovered,
            "after_metrics": avg_after_metrics,
            "anomalies_remaining": anomalies_remaining,
            "details": details,
        }
