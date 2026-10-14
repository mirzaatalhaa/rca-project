"""Incident report generation in JSON and Markdown formats."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
from src.incidents.models import IncidentReport
from src.config import settings

class IncidentReporter:
    """Persists incident reports to disk and creates markdown summaries."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or settings.REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_report(self, report: IncidentReport) -> tuple[Path, Path]:
        """Save report as canonical JSON and human-readable Markdown."""
        json_path = self.output_dir / f"{report.incident_id}.json"
        md_path = self.output_dir / f"{report.incident_id}.md"

        # 1. Canonical JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

        # 2. Markdown Report
        markdown_content = self.render_markdown(report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return json_path, md_path

    def render_markdown(self, r: IncidentReport) -> str:
        """Render markdown incident report."""
        status = r.recovery_verification.get("status", "UNKNOWN")
        status_badge = "✅ RECOVERED (SUCCESS)" if status == "SUCCESS" else ("❌ RECOVERY FAILED" if status == "FAILED" else "⚠️ INCONCLUSIVE")
        
        md = f"""# Incident Report: {r.incident_id}

**Generated At:** {r.iso_timestamp}  
**Scenario:** `{r.scenario_name}`  
**Affected Service:** `{r.affected_service}`  
**Recovery Status:** **{status_badge}**  
**Total Pipeline Execution Time:** `{r.execution_time_seconds:.2f}s`

---

## 1. Anomaly Detection
- **Detector:** `{r.anomaly_detection.get('detector_type')}`
- **Metric Flagged:** `{r.anomaly_detection.get('metric')}`
- **Observed Value:** `{r.anomaly_detection.get('observed_value')}` (Baseline: `{r.anomaly_detection.get('baseline_value')}`)
- **Severity / Score:** `{r.anomaly_detection.get('severity')}` (Score: `{r.anomaly_detection.get('score')}`)
- **Reason:** {r.anomaly_detection.get('reason')}

---

## 2. Root Cause Analysis (RCA)
- **Diagnosed Cause:** {r.rca_diagnosis.get('probable_root_cause')}
- **Confidence:** `{r.rca_diagnosis.get('confidence', 0.0) * 100:.1f}%`
- **Engine Provider:** `{r.rca_diagnosis.get('llm_provider')}` (Mock: `{r.rca_diagnosis.get('is_mock_result')}`)
- **Remediation Recommended:** `{r.rca_diagnosis.get('recommended_remediation')}`
- **Rationale:** {r.rca_diagnosis.get('remediation_rationale')}

### Supporting Evidence
"""
        for ev in r.supporting_evidence:
            md += f"- {ev}\n"

        md += f"""
---

## 3. Remediation Action Executed
- **Selected Action:** `{r.selected_action}`
- **Execution Status:** `{r.action_execution_result.get('status')}`
- **Policy Validation:** `{r.action_execution_result.get('policy_check')}`
- **Execution Latency:** `{r.action_execution_result.get('duration_ms', 0):.1f}ms`

---

## 4. Telemetry Telemetry: Before vs After Remediation

| Metric | Pre-Action (Incident) | Post-Action (Verified) | Baseline Expected |
|---|---|---|---|
"""
        for m, before_val in r.before_metrics.items():
            after_val = r.after_metrics.get(m, "N/A")
            baseline_val = r.anomaly_detection.get("baseline_value", "N/A") if m == r.anomaly_detection.get("metric") else "Nominal"
            md += f"| `{m}` | **{before_val}** | **{after_val}** | {baseline_val} |\n"

        md += f"""
---

## 5. Post-Action Recovery Verification
- **Verified Outcome:** **{r.recovery_verification.get('status')}**
- **Details:** {r.recovery_verification.get('details')}
"""

        if r.ground_truth_comparison:
            gt = r.ground_truth_comparison
            match_icon = "🎯 MATCH" if gt.get("matches_ground_truth") else "⚠️ MISMATCH"
            md += f"""
---

## 6. Ground-Truth Evaluation Benchmark
- **Evaluation Result:** **{match_icon}**
- **Expected Fault:** `{gt.get('ground_truth_fault')}`
- **Expected Remedy:** `{gt.get('expected_remediation')}`
- **Matched Remedy:** `{r.selected_action == gt.get('expected_remediation')}`
"""

        return md

    def list_reports(self) -> List[str]:
        """Return list of saved report IDs."""
        json_files = list(self.output_dir.glob("*.json"))
        return [f.stem for f in sorted(json_files, reverse=True)]

    def load_report(self, incident_id: str) -> Optional[IncidentReport]:
        """Load report by incident ID."""
        json_path = self.output_dir / f"{incident_id}.json"
        if not json_path.exists():
            return None
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return IncidentReport(**data)
