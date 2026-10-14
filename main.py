"""AI-Powered Self-Healing System - Command Line Interface (CLI).
Provides automated testing, scenario triggers, and benchmark execution.
"""
import sys
import argparse
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.pipeline import SelfHealingPipeline
from src.telemetry.simulator import SCENARIOS
from src.config import settings
from experiments.evaluate import run_evaluation_benchmark

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def print_banner():
    banner = """
=============================================================================
   [FLIGHTWATCH AI SELF-HEALING SYSTEM] - Autonomous SRE Testbed
   Telemetry Ingestion -> Anomaly Detection -> Context -> RCA -> Remediation
=============================================================================
"""
    print(banner)

def run_cli():
    parser = argparse.ArgumentParser(
        description="Autonomous AI Self-Healing System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="DATABASE_CONNECTION_FAILURE",
        choices=list(SCENARIOS.keys()) + list(SCENARIOS.values()),
        help="Simulated incident scenario to inject and remediate"
    )
    parser.add_argument(
        "--detector",
        type=str,
        default="both",
        choices=["statistical", "ml", "both"],
        help="Anomaly detector to use: statistical (Z-score), ml (Isolation Forest), or both"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=settings.LLM_PROVIDER,
        choices=["mock", "openai", "gemini"],
        help="LLM provider for root cause analysis (defaults to .env setting)"
    )
    parser.add_argument(
        "--no-remediate",
        action="store_true",
        help="Detect and diagnose only, skip executing automated remediation"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run full empirical benchmark evaluation across all 6 scenarios"
    )
    parser.add_argument(
        "--list-reports",
        action="store_true",
        help="List all saved incident reports in reports/ directory"
    )

    args = parser.parse_args()
    print_banner()

    if args.benchmark:
        print("[*] Running empirical evaluation benchmark...")
        run_evaluation_benchmark(num_trials_per_scenario=5)
        return

    pipeline = SelfHealingPipeline(llm_provider=args.provider)

    if args.list_reports:
        reports = pipeline.reporter.list_reports()
        print(f"[*] Found {len(reports)} generated incident report(s):")
        for r_id in reports:
            print(f"  - {r_id} (reports/{r_id}.json, reports/{r_id}.md)")
        return

    print(f"[*] Initializing pipeline...")
    print(f"    - LLM Provider: {args.provider.upper()}")
    print(f"    - Detector: {args.detector.upper()}")
    print(f"    - Auto-Remediation: {'DISABLED' if args.no_remediate else 'ENABLED'}")
    
    print("\n[Stage 1/6] Training baseline models on nominal telemetry stream...")
    pipeline.train_baseline(normal_steps=35)
    print("    ✓ Baseline training complete (Z-score parameters & Isolation Forest fitted)")

    scen_key = args.scenario.upper()
    print(f"\n[Stage 2/6] Injecting scenario: {scen_key}...")
    
    report, meta = pipeline.run_scenario(
        scenario_key=scen_key,
        detector_choice=args.detector,
        auto_remediate=(not args.no_remediate)
    )

    if report is None:
        print(f"    ✓ Scenario evaluated. Telemetry remained nominal: {meta.get('message')}")
        return

    print(f"\n[Stage 3/6] Anomaly Detected!")
    anom = report.anomaly_detection
    print(f"    - Metric: {anom.get('metric')}")
    print(f"    - Value Observed: {anom.get('observed_value')} (Baseline: {anom.get('baseline_value')})")
    print(f"    - Severity: {anom.get('severity').upper()} (Score: {anom.get('score')})")
    print(f"    - Detector: {anom.get('detector_type')}")
    print(f"    - Reason: {anom.get('reason')}")

    print(f"\n[Stage 4/6] Root Cause Analysis Completed (Incident {report.incident_id})")
    rca = report.rca_diagnosis
    print(f"    - Probable Root Cause: {rca.get('probable_root_cause')}")
    print(f"    - Confidence: {rca.get('confidence', 0.0) * 100:.1f}%")
    print(f"    - Engine Provider: {rca.get('llm_provider')} (Mock: {rca.get('is_mock_result')})")
    print(f"    - Recommended Action: {rca.get('recommended_remediation')}")
    print(f"    - Rationale: {rca.get('remediation_rationale')}")

    if not args.no_remediate:
        print(f"\n[Stage 5/6] Policy Validation & Remediation Execution")
        act = report.action_execution_result
        print(f"    - Policy Check: {act.get('policy_check')}")
        print(f"    - Executed Action: {report.selected_action}")
        print(f"    - Execution Status: {act.get('status')} ({act.get('duration_ms', 0):.1f}ms)")

        print(f"\n[Stage 6/6] Post-Action Verification & Health Check")
        ver = report.recovery_verification
        status_symbol = "[RECOVERED]" if ver.get("recovered") else "[FAILED]"
        print(f"    - Outcome: {status_symbol} {ver.get('status')}")
        print(f"    - Verification Details: {ver.get('details')}")

        print("\n--- Telemetry Metrics (Before vs After Remediation) ---")
        for m, before_v in report.before_metrics.items():
            after_v = report.after_metrics.get(m, "N/A")
            print(f"    * {m:<26}: {before_v:>8}  ->  {after_v:>8}")

    if report.ground_truth_comparison:
        gt = report.ground_truth_comparison
        match_icon = "[MATCH]" if gt.get("matches_ground_truth") else "[MISMATCH]"
        print(f"\n[Evaluation Ground-Truth Benchmark: {match_icon}]")
        print(f"    - Expected Fault: {gt.get('ground_truth_fault')}")
        print(f"    - Expected Remedy: {gt.get('expected_remediation')}")

    print("\n" + "=" * 75)
    print(f"[SUCCESS] Incident Report Successfully Generated:")
    print(f"    - JSON:     {meta.get('json_path')}")
    print(f"    - Markdown: {meta.get('markdown_path')}")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    run_cli()
