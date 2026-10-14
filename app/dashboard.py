"""Streamlit Interactive Web Dashboard for AI-Powered Self-Healing System.
Visualizes live telemetry streams, anomaly detection, LLM RCA diagnosis,
policy engine validation, simulated remediation, and post-action recovery verification.
"""
import sys
import time
from pathlib import Path
import streamlit as st
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.pipeline import SelfHealingPipeline
from src.telemetry.simulator import SCENARIOS
from src.config import settings
from src.incidents.reporter import IncidentReporter

st.set_page_config(
    page_title="FlightWatch AI Self-Healing System",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        border: 1px solid #e9ecef;
    }
    .badge-success {
        background-color: #28a745;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-danger {
        background-color: #dc3545;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("✈️ FlightWatch AI Self-Healing System")
st.caption("Autonomous Cloud Observability, Anomaly Detection, LLM Root Cause Analysis & Policy Remediation Engine")

# Sidebar Controls
st.sidebar.header("🕹️ Simulation Controls")

selected_scenario = st.sidebar.selectbox(
    "Select Failure Scenario",
    options=list(SCENARIOS.keys()),
    index=list(SCENARIOS.keys()).index("DATABASE_CONNECTION_FAILURE")
)

selected_detector = st.sidebar.selectbox(
    "Anomaly Detector",
    options=["both", "statistical", "ml"],
    format_func=lambda x: "Both (Ensemble)" if x == "both" else ("Statistical (Z-score)" if x == "statistical" else "ML (Isolation Forest)")
)

llm_provider = st.sidebar.selectbox(
    "LLM RCA Provider",
    options=["mock", "openai", "gemini"],
    index=0,
    help="Select 'mock' for offline rule-based diagnosis, or 'openai'/'gemini' if API keys are configured."
)

auto_remediate = st.sidebar.checkbox("Enable Automated Remediation", value=True)

run_button = st.sidebar.button("🚀 Trigger Scenario & Execute Pipeline", type="primary", use_container_width=True)

# Main Dashboard Tabs
tab_pipeline, tab_telemetry, tab_history = st.tabs(["⚡ Self-Healing Pipeline", "📈 Telemetry Streams", "📋 Incident History"])

if "pipeline" not in st.session_state:
    with st.spinner("Initializing models and baseline telemetry..."):
        p = SelfHealingPipeline(llm_provider=llm_provider)
        p.train_baseline(normal_steps=35)
        st.session_state.pipeline = p
        st.session_state.reporter = IncidentReporter()
        st.session_state.last_report = None
        st.session_state.last_meta = None

pipeline: SelfHealingPipeline = st.session_state.pipeline
pipeline.rca_analyzer.provider = llm_provider

if run_button:
    # Reset loop protection for manual demonstration
    pipeline.policy_engine.reset_history()
    
    with st.status(f"Executing self-healing workflow for '{selected_scenario}'...", expanded=True) as status:
        st.write("1. 📡 Generating synthetic telemetry & evaluating incoming stream...")
        time.sleep(0.3)
        
        report, meta = pipeline.run_scenario(
            scenario_key=selected_scenario,
            detector_choice=selected_detector,
            auto_remediate=auto_remediate
        )
        st.session_state.last_report = report
        st.session_state.last_meta = meta

        if report is None:
            st.write("2. 🟢 No anomalies flagged - system operating in nominal baseline.")
            status.update(label="Normal Operation: Telemetry Healthy", state="complete")
        else:
            st.write(f"2. ⚠️ Anomaly Detected on `{report.anomaly_detection.get('metric')}` (Score: {report.anomaly_detection.get('score')})")
            time.sleep(0.2)
            st.write(f"3. 🔍 Context Retrieved: {len(report.supporting_evidence)} evidence signals isolated.")
            time.sleep(0.2)
            st.write(f"4. 🧠 LLM Root Cause Analysis completed ({report.rca_diagnosis.get('llm_provider')}).")
            time.sleep(0.2)
            if auto_remediate:
                st.write(f"5. 🛡️ Remediation Policy Check: `{report.action_execution_result.get('policy_check')}`. Executing: `{report.selected_action}`.")
                time.sleep(0.2)
                st.write(f"6. ✅ Post-Action Verification: `{report.recovery_verification.get('status')}`.")
            status.update(label="Self-Healing Pipeline Completed!", state="complete")

# Display current pipeline execution state
with tab_pipeline:
    report = st.session_state.last_report
    if report is None:
        st.info("👈 Select a failure scenario from the sidebar and click **'Trigger Scenario & Execute Pipeline'** to begin.")
    else:
        # Header banner
        is_recovered = report.recovery_verification.get("recovered", False)
        status_color = "green" if is_recovered else "red"
        st.subheader(f"Incident: `{report.incident_id}` | Scenario: {report.scenario_name}")
        
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            st.metric("Primary Metric Flagged", report.anomaly_detection.get("metric"))
        with col_s2:
            st.metric("Observed Anomaly Value", report.anomaly_detection.get("observed_value"))
        with col_s3:
            st.metric("RCA Confidence", f"{report.rca_diagnosis.get('confidence', 0.0) * 100:.0f}%")
        with col_s4:
            st.metric("Verification Status", report.recovery_verification.get("status"))

        st.divider()

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("### 🔍 1. Anomaly Detection & Context")
            st.json(report.anomaly_detection)

            st.markdown("### 📋 Evidence Logs & Spans")
            for ev in report.supporting_evidence:
                st.markdown(f"- `{ev}`")

        with col_right:
            st.markdown("### 🧠 2. LLM Root Cause Diagnosis")
            st.success(f"**Probable Cause:** {report.rca_diagnosis.get('probable_root_cause')}")
            st.info(f"**Remediation Recommendation:** `{report.rca_diagnosis.get('recommended_remediation')}`")
            st.write(f"**Rationale:** {report.rca_diagnosis.get('remediation_rationale')}")
            st.caption(f"Engine: {report.rca_diagnosis.get('llm_provider')} | Mock Mode: {report.rca_diagnosis.get('is_mock_result')}")

            st.markdown("### 🛡️ 3. Remediation & Verification")
            st.write(f"**Action Executed:** `{report.selected_action}`")
            st.write(f"**Policy Check:** `{report.action_execution_result.get('policy_check')}`")
            st.write(f"**Recovery Outcome:** **{report.recovery_verification.get('status')}**")
            st.write(f"**Verification Details:** {report.recovery_verification.get('details')}")

        st.divider()
        st.markdown("### 📊 Pre-Remediation vs Post-Remediation Telemetry")
        metrics_df = pd.DataFrame([
            {"Metric": m, "Incident (Pre-Action)": report.before_metrics.get(m), "Verified (Post-Action)": report.after_metrics.get(m)}
            for m in settings.TRACKED_METRICS
        ])
        st.dataframe(metrics_df, use_container_width=True)

with tab_telemetry:
    st.subheader("📈 Real-time Service Telemetry")
    if st.session_state.last_report:
        report = st.session_state.last_report
        chart_data = pd.DataFrame({
            "Pre-Action (Fault State)": report.before_metrics,
            "Post-Action (Recovered State)": report.after_metrics
        })
        st.bar_chart(chart_data)
    else:
        st.info("Run a scenario to view comparative telemetry charts.")

with tab_history:
    st.subheader("📁 Persisted Incident Reports")
    reporter: IncidentReporter = st.session_state.reporter
    report_list = reporter.list_reports()
    
    if not report_list:
        st.write("No incident reports found in `reports/` directory.")
    else:
        selected_hist_id = st.selectbox("Select Incident Report to Inspect", report_list)
        if selected_hist_id:
            hist_report = reporter.load_report(selected_hist_id)
            if hist_report:
                st.markdown(f"**Scenario:** `{hist_report.scenario_name}` | **Generated:** `{hist_report.iso_timestamp}`")
                st.markdown(reporter.render_markdown(hist_report))
                with st.expander("View Raw JSON Artifact"):
                    st.json(hist_report.model_dump())
