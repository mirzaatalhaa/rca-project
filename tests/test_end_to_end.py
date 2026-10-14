"""End-to-End integration tests for SelfHealingPipeline."""
import pytest
from src.orchestrator.pipeline import SelfHealingPipeline
from src.telemetry.simulator import SCENARIOS

@pytest.fixture(scope="function")
def trained_pipeline():
    pipeline = SelfHealingPipeline(llm_provider="mock")
    pipeline.train_baseline(normal_steps=30)
    return pipeline

def test_pipeline_normal_operation_no_incident(trained_pipeline):
    report, meta = trained_pipeline.run_scenario("NORMAL_OPERATION", auto_remediate=False)
    assert report is None
    assert meta["status"] == "HEALTHY"

@pytest.mark.parametrize("scenario_key", [
    "HIGH_LATENCY",
    "ELEVATED_HTTP_ERROR_RATE",
    "DATABASE_CONNECTION_FAILURE",
    "CPU_MEMORY_PRESSURE",
    "CASCADING_FAILURE"
])
def test_pipeline_all_incident_scenarios_remediate_and_recover(trained_pipeline, scenario_key):
    # Reset loop protection before each scenario
    trained_pipeline.policy_engine.reset_history()
    
    report, meta = trained_pipeline.run_scenario(scenario_key, auto_remediate=True)
    assert report is not None
    assert report.incident_id.startswith("INC-")
    assert report.action_execution_result["status"] == "SUCCESS"
    assert report.recovery_verification["recovered"] is True
    assert report.recovery_verification["status"] == "SUCCESS"
    assert meta["status"] == "ANOMALY_RESOLVED"
    assert "json_path" in meta
