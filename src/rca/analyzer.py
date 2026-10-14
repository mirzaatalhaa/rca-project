"""RCA Analyzer supporting LLM providers (OpenAI, Gemini) with robust mock/fallback mode.
Guarantees structured RCADiagnosis output conforming to schema and allowlists.
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from src.context.models import IncidentContext
from src.rca.models import RCADiagnosis
from src.rca.prompt import build_rca_prompt
from src.config import settings

logger = logging.getLogger(__name__)

class RCAAnalyzer:
    """Diagnoses incidents using configured LLM provider or fallback mock mode."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or settings.LLM_PROVIDER).lower()

    def diagnose(self, context: IncidentContext) -> RCADiagnosis:
        """Run root cause analysis on the provided incident context."""
        if self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                return self._call_openai(context)
            except Exception as e:
                logger.warning(f"OpenAI RCA call failed ({e}). Falling back to Mock RCA.")
                res = self._run_mock_rca(context)
                res.llm_provider = f"mock (fallback from openai error: {str(e)[:60]})"
                return res

        elif self.provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                return self._call_gemini(context)
            except Exception as e:
                logger.warning(f"Gemini RCA call failed ({e}). Falling back to Mock RCA.")
                res = self._run_mock_rca(context)
                res.llm_provider = f"mock (fallback from gemini error: {str(e)[:60]})"
                return res

        # Default or fallback mode
        return self._run_mock_rca(context)

    def _call_openai(self, context: IncidentContext) -> RCADiagnosis:
        """Call OpenAI API using REST request."""
        sys_prompt, user_prompt = build_rca_prompt(context)
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            
            # Ensure action is in allowlist
            action = parsed.get("recommended_remediation")
            if action not in settings.ALLOWED_ACTIONS:
                action = "restart_service"

            return RCADiagnosis(
                incident_id=context.incident_id,
                affected_service=context.affected_service,
                detected_symptoms=parsed.get("detected_symptoms", [context.anomaly_event.metric]),
                probable_root_cause=parsed.get("probable_root_cause", "Unspecified root cause"),
                supporting_evidence=parsed.get("supporting_evidence", [context.anomaly_event.reason]),
                alternative_hypotheses=parsed.get("alternative_hypotheses", []),
                severity=parsed.get("severity", context.anomaly_event.severity),
                confidence=float(parsed.get("confidence", 0.85)),
                recommended_remediation=action,
                remediation_rationale=parsed.get("remediation_rationale", "Restores normal service state"),
                llm_provider=f"openai ({settings.OPENAI_MODEL})",
                is_mock_result=False
            )

    def _call_gemini(self, context: IncidentContext) -> RCADiagnosis:
        """Call Google Gemini REST API."""
        sys_prompt, user_prompt = build_rca_prompt(context)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{sys_prompt}\n\n{user_prompt}"}]}
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(content)

            action = parsed.get("recommended_remediation")
            if action not in settings.ALLOWED_ACTIONS:
                action = "restart_service"

            return RCADiagnosis(
                incident_id=context.incident_id,
                affected_service=context.affected_service,
                detected_symptoms=parsed.get("detected_symptoms", [context.anomaly_event.metric]),
                probable_root_cause=parsed.get("probable_root_cause", "Unspecified root cause"),
                supporting_evidence=parsed.get("supporting_evidence", [context.anomaly_event.reason]),
                alternative_hypotheses=parsed.get("alternative_hypotheses", []),
                severity=parsed.get("severity", context.anomaly_event.severity),
                confidence=float(parsed.get("confidence", 0.85)),
                recommended_remediation=action,
                remediation_rationale=parsed.get("remediation_rationale", "Restores normal service state"),
                llm_provider=f"gemini ({settings.GEMINI_MODEL})",
                is_mock_result=False
            )

    def _run_mock_rca(self, context: IncidentContext) -> RCADiagnosis:
        """Deterministic heuristic rule-based RCA for offline/development testing.
        Clearly labeled as mock mode to avoid misleading evaluation.
        """
        metric = context.anomaly_event.metric
        log_texts = " ".join([l.get("message", "") for l in context.relevant_logs]).lower()
        metrics = context.metrics_summary

        # Check cascading signatures first
        is_cascading = (
            "cascading" in log_texts or
            (metrics.get("memory_utilization_pct", {}).get("latest", 0) > 85 and
             metrics.get("db_connection_usage", {}).get("latest", 0) > 80 and
             metrics.get("http_error_rate_pct", {}).get("latest", 0) > 40)
        )

        if is_cascading:
            return RCADiagnosis(
                incident_id=context.incident_id,
                affected_service=context.affected_service,
                detected_symptoms=[
                    "High memory consumption exceeding 95%",
                    "Database connection pool starvation (100% saturation)",
                    "Cascading HTTP 500 error surge"
                ],
                probable_root_cause="Cascading system-wide resource starvation initiated by memory buffer saturation propagating to database connection timeout",
                supporting_evidence=[
                    "Log: Cascading failure detected: OutOfMemoryError impending",
                    f"Memory utilization at {metrics.get('memory_utilization_pct', {}).get('latest', 95)}%",
                    f"DB connections at {metrics.get('db_connection_usage', {}).get('latest', 100)}"
                ],
                alternative_hypotheses=["Underlying physical host resource contention", "DDoS attack overwhelming gateway"],
                severity="critical",
                confidence=0.95,
                recommended_remediation="restart_service",
                remediation_rationale="Executing service restart clears corrupted memory buffers and resets all active database pool connections cleanly",
                llm_provider="mock (heuristic rule-engine)",
                is_mock_result=True
            )

        # Database pool failure
        if "pool exhausted" in log_texts or "db_connection_usage" == metric or metrics.get("db_connection_usage", {}).get("latest", 0) >= 90:
            return RCADiagnosis(
                incident_id=context.incident_id,
                affected_service=context.affected_service,
                detected_symptoms=[
                    "Database connection pool at 100% capacity",
                    "HTTP 503 service unavailable responses",
                    "Client connection acquisition timeout errors"
                ],
                probable_root_cause="Database connection pool starvation caused by unclosed transaction leaks under sustained load",
                supporting_evidence=[
                    "Log: Database connection pool exhausted: Active connections 100/100",
                    f"Observed db_connection_usage: {context.anomaly_event.observed_value}"
                ],
                alternative_hypotheses=["Database server offline or unreachable", "Network socket exhaustion"],
                severity="critical",
                confidence=0.92,
                recommended_remediation="reset_database_connection_pool",
                remediation_rationale="Resetting the connection pool flushes orphaned connection handles and recreates the pool without taking down the entire service",
                llm_provider="mock (heuristic rule-engine)",
                is_mock_result=True
            )

        # Memory / CPU pressure
        if "heap" in log_texts or "garbage collection" in log_texts or metric in ("memory_utilization_pct", "cpu_utilization_pct") or metrics.get("memory_utilization_pct", {}).get("latest", 0) >= 85:
            return RCADiagnosis(
                incident_id=context.incident_id,
                affected_service=context.affected_service,
                detected_symptoms=[
                    f"Elevated {metric} exceeding 90% threshold",
                    "Major garbage collection pauses triggering thread delays"
                ],
                probable_root_cause="Unbounded in-memory telemetry cache retention creating memory leak and CPU garbage collector thrashing",
                supporting_evidence=[
                    f"Observed metric {metric} value {context.anomaly_event.observed_value}",
                    "Log: High resource pressure: CPU/memory heap consumption high"
                ],
                alternative_hypotheses=["Sudden traffic surge beyond provisioned capacity"],
                severity="high",
                confidence=0.90,
                recommended_remediation="clear_memory_leak",
                remediation_rationale="Flushing in-memory caches and triggering aggressive garbage collection reclaims heap headroom safely",
                llm_provider="mock (heuristic rule-engine)",
                is_mock_result=True
            )

        # HTTP error rate spike
        if "null pointer" in log_texts or "internal server error" in log_texts or metric == "http_error_rate_pct" or metrics.get("http_error_rate_pct", {}).get("latest", 0) >= 30:
            return RCADiagnosis(
                incident_id=context.incident_id,
                affected_service=context.affected_service,
                detected_symptoms=[
                    f"HTTP error rate spiked to {context.anomaly_event.observed_value}%",
                    "HTTP 500 error traces observed in telemetry feed"
                ],
                probable_root_cause="Unhandled exception in radar feeder controller causing unrecovered thread crashes",
                supporting_evidence=[
                    "Log: Internal Server Error: Unhandled exception in FlightController",
                    f"Observed error rate {context.anomaly_event.observed_value}%"
                ],
                alternative_hypotheses=["Upstream malformed API payload", "Corrupted cached schema"],
                severity="high",
                confidence=0.88,
                recommended_remediation="restart_service",
                remediation_rationale="Restarting the service worker cleans up crashed threads and resets the controller to safe baseline state",
                llm_provider="mock (heuristic rule-engine)",
                is_mock_result=True
            )

        # High latency
        return RCADiagnosis(
            incident_id=context.incident_id,
            affected_service=context.affected_service,
            detected_symptoms=[
                f"Request latency exceeded threshold at {context.anomaly_event.observed_value}ms",
                "Slow database queries observed in trace spans"
            ],
            probable_root_cause="Unindexed query join causing backend thread queue saturation and high request latency",
            supporting_evidence=[
                f"Observed latency {context.anomaly_event.observed_value}ms vs baseline {context.anomaly_event.baseline_value}ms",
                "Trace: Duration > 2000ms on flight search operations"
            ],
            alternative_hypotheses=["Transient network packet drop", "Downstream third-party flight feed slowdown"],
            severity="medium",
            confidence=0.86,
            recommended_remediation="reduce_simulated_load",
            remediation_rationale="Enabling temporary rate-limiting / load throttling drains saturated thread queues and prevents full outage",
            llm_provider="mock (heuristic rule-engine)",
            is_mock_result=True
        )
