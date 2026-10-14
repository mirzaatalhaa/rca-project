"""End-to-End Self-Healing Pipeline Coordinator.
Connects Telemetry Generator -> Ingestion -> Detection -> Context -> RCA -> Policy -> Remediation -> Verification -> Incident Report.
"""
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from src.telemetry.simulator import TelemetrySimulator, SCENARIOS
from src.telemetry.ingestion import TelemetryIngestionBuffer
from src.detection.statistical import StatisticalZScoreDetector
from src.detection.ml_detector import IsolationForestDetector
from src.context.retriever import ContextRetriever
from src.rca.analyzer import RCAAnalyzer
from src.remediation.policy import RemediationPolicyEngine
from src.remediation.executor import RemediationExecutor
from src.orchestrator.verifier import PostActionVerifier
from src.incidents.reporter import IncidentReporter
from src.incidents.models import IncidentReport
from src.config import settings

class SelfHealingPipeline:
    """Orchestrates the entire automated detection, diagnosis, remediation, and verification loop."""

    def __init__(
        self,
        service_name: str = "flight-api",
        llm_provider: Optional[str] = None,
        z_threshold: Optional[float] = None,
        contamination: Optional[float] = None
    ):
        self.service_name = service_name
        self.simulator = TelemetrySimulator(seed=42, service_name=service_name)
        self.buffer = TelemetryIngestionBuffer()
        
        # Detectors
        self.stat_detector = StatisticalZScoreDetector(threshold_z=z_threshold)
        self.ml_detector = IsolationForestDetector(contamination=contamination)
        
        # Pipeline components
        self.context_retriever = ContextRetriever(self.buffer, window_seconds=60.0)
        self.rca_analyzer = RCAAnalyzer(provider=llm_provider)
        self.policy_engine = RemediationPolicyEngine(max_retries=settings.MAX_REMEDIATION_RETRIES)
        self.executor = RemediationExecutor(self.policy_engine)
        self.verifier = PostActionVerifier(self.stat_detector, verification_steps=5)
        self.reporter = IncidentReporter()
        self.is_trained = False

    def train_baseline(self, normal_steps: int = 35, step_seconds: float = 10.0) -> None:
        """Collect healthy baseline telemetry to fit statistical and ML detectors."""
        self.simulator.reset()
        self.buffer.clear()
        base_time = time.time() - (normal_steps * step_seconds)
        all_metrics = []

        for i in range(normal_steps):
            t = base_time + (i * step_seconds)
            pts, logs, traces = self.simulator.generate_point_in_time(t)
            self.buffer.ingest_batch(pts, logs, traces)
            all_metrics.extend(pts)

        # Fit detectors
        self.stat_detector.fit(all_metrics)
        self.ml_detector.fit(all_metrics)
        self.is_trained = True

    def run_scenario(
        self,
        scenario_key: str,
        detector_choice: str = "both",
        auto_remediate: bool = True
    ) -> Tuple[Optional[IncidentReport], Dict[str, Any]]:
        """Run an end-to-end incident scenario.
        Returns: (IncidentReport, execution_metadata)
        """
        if not self.is_trained:
            self.train_baseline()

        pipeline_start = time.time()
        scenario_val = SCENARIOS.get(scenario_key.upper(), scenario_key.lower())
        
        # Inject fault if scenario is non-normal
        self.simulator.inject_fault(scenario_val)
        ground_truth = self.simulator.get_ground_truth(scenario_val, time.time())

        # Simulate incoming stream
        detected_event = None
        current_time = time.time()
        pre_action_snapshot: Dict[str, float] = {}

        # Stream 8 telemetry batches
        for step in range(8):
            step_time = current_time + (step * 5.0)
            pts, logs, traces = self.simulator.generate_point_in_time(step_time)
            self.buffer.ingest_batch(pts, logs, traces)

            # Keep latest metric snapshot
            for p in pts:
                pre_action_snapshot[p.metric] = p.value

            # Check detection
            if detected_event is None:
                if detector_choice in ("statistical", "both"):
                    for p in pts:
                        evt = self.stat_detector.detect(p)
                        if evt and evt.is_anomaly:
                            detected_event = evt
                            break

                if detected_event is None and detector_choice in ("ml", "both"):
                    ml_evt = self.ml_detector.detect_multivariate(pts)
                    if ml_evt and ml_evt.is_anomaly:
                        detected_event = ml_evt

        # If normal operation or no anomaly detected
        if detected_event is None:
            return None, {
                "scenario": scenario_val,
                "status": "HEALTHY",
                "message": "No anomalies detected in telemetry stream.",
                "duration_seconds": round(time.time() - pipeline_start, 2)
            }

        # 1. Retrieve Context
        context = self.context_retriever.retrieve_context(detected_event)

        # 2. LLM Root Cause Analysis
        rca = self.rca_analyzer.diagnose(context)

        # 3. Remediation Execution
        action_result = {
            "action": rca.recommended_remediation,
            "status": "SKIPPED",
            "policy_check": "BYPASSED",
            "duration_ms": 0.0,
            "error": "Auto-remediation disabled by user flag."
        }
        verification_result = {
            "status": "NOT_RUN",
            "recovered": False,
            "details": "Auto-remediation was not executed."
        }
        after_metrics = dict(pre_action_snapshot)

        if auto_remediate:
            action_result = self.executor.execute(
                action=rca.recommended_remediation,
                service=self.service_name,
                simulator=self.simulator
            )

            # 4. Post-Action Verification
            verification_result = self.verifier.verify_recovery(
                simulator=self.simulator,
                pre_action_metrics=pre_action_snapshot,
                target_service=self.service_name
            )
            after_metrics = verification_result.get("after_metrics", pre_action_snapshot)

        # 5. Ground Truth Evaluation
        matches_gt = (
            ground_truth.expected_remediation == rca.recommended_remediation or
            ground_truth.scenario_name.lower() in rca.probable_root_cause.lower()
        )
        gt_comparison = {
            "scenario_id": ground_truth.scenario_id,
            "ground_truth_fault": ground_truth.fault_injected,
            "ground_truth_cause": ground_truth.primary_root_cause,
            "expected_remediation": ground_truth.expected_remediation,
            "matches_ground_truth": matches_gt,
            "recommended_action_matched": (ground_truth.expected_remediation == rca.recommended_remediation),
        }

        # 6. Generate & Save Incident Report
        total_pipeline_time = time.time() - pipeline_start
        report = IncidentReport(
            incident_id=context.incident_id,
            timestamp=detected_event.timestamp,
            iso_timestamp=datetime.now(timezone.utc).iso_format() if hasattr(datetime.now(timezone.utc), 'iso_format') else datetime.now(timezone.utc).isoformat(),
            scenario_name=ground_truth.scenario_name,
            affected_service=self.service_name,
            anomaly_detection=detected_event.model_dump(),
            supporting_evidence=rca.supporting_evidence,
            rca_diagnosis=rca.model_dump(),
            selected_action=rca.recommended_remediation,
            action_execution_result=action_result,
            before_metrics=pre_action_snapshot,
            after_metrics=after_metrics,
            recovery_verification=verification_result,
            ground_truth_comparison=gt_comparison,
            execution_time_seconds=round(total_pipeline_time, 2)
        )

        json_path, md_path = self.reporter.save_report(report)

        meta = {
            "scenario": scenario_val,
            "status": "ANOMALY_RESOLVED" if verification_result.get("recovered") else "REMEDIATION_FAILED",
            "incident_id": report.incident_id,
            "json_path": str(json_path),
            "markdown_path": str(md_path),
            "duration_seconds": round(total_pipeline_time, 2)
        }
        return report, meta
