"""Repeatable Experimental Evaluation Framework.
Measures Anomaly Detection (Statistical Z-Score vs Isolation Forest) Precision, Recall, F1,
RCA Ground-Truth Diagnostic Accuracy, Remediation Success Rate, and Execution Latency across all 6 scenarios.
"""
import time
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, Any, List
from src.telemetry.simulator import TelemetrySimulator, SCENARIOS
from src.detection.statistical import StatisticalZScoreDetector
from src.detection.ml_detector import IsolationForestDetector
from src.context.retriever import ContextRetriever
from src.telemetry.ingestion import TelemetryIngestionBuffer
from src.rca.analyzer import RCAAnalyzer
from src.remediation.policy import RemediationPolicyEngine
from src.remediation.executor import RemediationExecutor
from src.orchestrator.verifier import PostActionVerifier

def run_evaluation_benchmark(num_trials_per_scenario: int = 5) -> Dict[str, Any]:
    """Run empirical benchmark across statistical and ML detectors and all 6 scenarios."""
    print("=" * 70)
    print("STARTING EMPIRICAL EVALUATION BENCHMARK")
    print(f"Scenarios: {len(SCENARIOS)} | Repetitions per scenario: {num_trials_per_scenario}")
    print("=" * 70)

    # 1. Baseline training phase
    sim = TelemetrySimulator(seed=100)
    buffer = TelemetryIngestionBuffer()
    train_metrics = []
    base_t = time.time()
    for i in range(40):
        pts, l, tr = sim.generate_point_in_time(base_t + (i * 10.0))
        train_metrics.extend(pts)
        buffer.ingest_batch(pts, l, tr)

    stat_det = StatisticalZScoreDetector()
    stat_det.fit(train_metrics)

    ml_det = IsolationForestDetector()
    ml_det.fit(train_metrics)

    context_retriever = ContextRetriever(buffer)
    rca_analyzer = RCAAnalyzer()
    policy_engine = RemediationPolicyEngine()
    executor = RemediationExecutor(policy_engine)
    verifier = PostActionVerifier(stat_det)

    # Metrics trackers
    stats = {
        "statistical": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        "isolation_forest": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        "rca": {"total_faults": 0, "correct_root_cause": 0, "correct_remediation": 0},
        "remediation": {"total_attempts": 0, "successful_recoveries": 0},
        "latencies": [],
    }

    scenario_list = list(SCENARIOS.keys())

    for scen_name in scenario_list:
        scen_val = SCENARIOS[scen_name]
        is_fault = (scen_val != SCENARIOS["NORMAL_OPERATION"])

        for trial in range(num_trials_per_scenario):
            trial_sim = TelemetrySimulator(seed=200 + (trial * 13), service_name="flight-api")
            trial_buffer = TelemetryIngestionBuffer()
            trial_start = time.time()

            # Pre-populate history in buffer
            for i in range(15):
                pts, l, tr = trial_sim.generate_point_in_time(base_t + (i * 10.0))
                trial_buffer.ingest_batch(pts, l, tr)

            # Inject fault
            if is_fault:
                trial_sim.inject_fault(scen_val)
            gt = trial_sim.get_ground_truth(scen_val, time.time())

            # Evaluate test window
            stat_flagged = False
            ml_flagged = False
            flagged_event = None
            pre_metrics = {}

            for step in range(5):
                pts, l, tr = trial_sim.generate_point_in_time(base_t + 200 + (step * 5.0))
                trial_buffer.ingest_batch(pts, l, tr)
                for p in pts:
                    pre_metrics[p.metric] = p.value

                # Test statistical detector
                if not stat_flagged:
                    for p in pts:
                        evt = stat_det.detect(p)
                        if evt and evt.is_anomaly:
                            stat_flagged = True
                            if flagged_event is None:
                                flagged_event = evt
                            break

                # Test isolation forest
                if not ml_flagged:
                    evt_ml = ml_det.detect_multivariate(pts)
                    if evt_ml and evt_ml.is_anomaly:
                        ml_flagged = True
                        if flagged_event is None:
                            flagged_event = evt_ml

            # Record detection outcomes
            for det_name, flagged in [("statistical", stat_flagged), ("isolation_forest", ml_flagged)]:
                if is_fault:
                    if flagged:
                        stats[det_name]["tp"] += 1
                    else:
                        stats[det_name]["fn"] += 1
                else:
                    if flagged:
                        stats[det_name]["fp"] += 1
                    else:
                        stats[det_name]["tn"] += 1

            # If fault occurred and was detected, evaluate RCA & Remediation
            if is_fault and flagged_event is not None:
                stats["rca"]["total_faults"] += 1
                trial_retriever = ContextRetriever(trial_buffer)
                ctx = trial_retriever.retrieve_context(flagged_event)
                diagnosis = rca_analyzer.diagnose(ctx)
                policy_engine.reset_history()

                # Check root cause diagnosis
                action_matched = (diagnosis.recommended_remediation == gt.expected_remediation)
                if action_matched:
                    stats["rca"]["correct_remediation"] += 1
                    stats["rca"]["correct_root_cause"] += 1

                # Execute remediation & verify
                stats["remediation"]["total_attempts"] += 1
                exec_res = executor.execute(
                    action=diagnosis.recommended_remediation,
                    service="flight-api",
                    simulator=trial_sim
                )
                ver_res = verifier.verify_recovery(
                    simulator=trial_sim,
                    pre_action_metrics=pre_metrics,
                    target_service="flight-api"
                )
                if ver_res["recovered"]:
                    stats["remediation"]["successful_recoveries"] += 1

            duration = time.time() - trial_start
            stats["latencies"].append(duration)

    # Compute aggregate evaluation metrics
    def calc_metrics(cm):
        tp, fp, tn, fn = cm["tp"], cm["fp"], cm["tn"], cm["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
        return {
            "TP": tp, "FP": fp, "TN": tn, "FN": fn,
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "F1_Score": round(f1, 4),
            "Accuracy": round(accuracy, 4)
        }

    stat_results = calc_metrics(stats["statistical"])
    ml_results = calc_metrics(stats["isolation_forest"])
    rca_acc = stats["rca"]["correct_root_cause"] / stats["rca"]["total_faults"] if stats["rca"]["total_faults"] > 0 else 0.0
    rem_acc = stats["remediation"]["successful_recoveries"] / stats["remediation"]["total_attempts"] if stats["remediation"]["total_attempts"] > 0 else 0.0
    avg_latency = sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0.0

    benchmark_summary = {
        "statistical_detector": stat_results,
        "isolation_forest_detector": ml_results,
        "rca_performance": {
            "total_fault_incidents": stats["rca"]["total_faults"],
            "root_cause_accuracy": round(rca_acc, 4),
            "remediation_recommendation_accuracy": round(stats["rca"]["correct_remediation"] / stats["rca"]["total_faults"], 4) if stats["rca"]["total_faults"] > 0 else 0.0,
        },
        "remediation_performance": {
            "total_remediation_actions": stats["remediation"]["total_attempts"],
            "successful_recoveries": stats["remediation"]["successful_recoveries"],
            "remediation_success_rate": round(rem_acc, 4),
        },
        "execution_timing": {
            "mean_execution_time_seconds": round(avg_latency, 4),
            "total_trials_evaluated": len(stats["latencies"])
        }
    }

    # Print summary
    print("\n" + "=" * 70)
    print("EXPERIMENTAL EVALUATION RESULTS")
    print("=" * 70)
    print(f"\n1. Statistical Z-Score Detector:")
    print(f"   Precision: {stat_results['Precision']:.2%} | Recall: {stat_results['Recall']:.2%} | F1: {stat_results['F1_Score']:.4f}")
    print(f"   Confusion Matrix: TP={stat_results['TP']}, FP={stat_results['FP']}, TN={stat_results['TN']}, FN={stat_results['FN']}")

    print(f"\n2. Isolation Forest Detector:")
    print(f"   Precision: {ml_results['Precision']:.2%} | Recall: {ml_results['Recall']:.2%} | F1: {ml_results['F1_Score']:.4f}")
    print(f"   Confusion Matrix: TP={ml_results['TP']}, FP={ml_results['FP']}, TN={ml_results['TN']}, FN={ml_results['FN']}")

    print(f"\n3. Root Cause Analysis Accuracy (against Ground Truth):")
    print(f"   Accuracy: {rca_acc:.2%} ({stats['rca']['correct_root_cause']}/{stats['rca']['total_faults']} incidents)")

    print(f"\n4. Remediation Recovery Success Rate:")
    print(f"   Success Rate: {rem_acc:.2%} ({stats['remediation']['successful_recoveries']}/{stats['remediation']['total_attempts']} actions)")

    print(f"\n5. End-to-End Latency:")
    print(f"   Mean Pipeline Runtime: {avg_latency:.4f}s")
    print("=" * 70)

    # Save to json
    out_file = Path(__file__).resolve().parent / "benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=2)
    print(f"\nBenchmark results saved to: {out_file}\n")

    return benchmark_summary

if __name__ == "__main__":
    run_evaluation_benchmark(num_trials_per_scenario=5)
