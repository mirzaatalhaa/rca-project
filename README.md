# FlightWatch AI Self-Healing System

Autonomous AI-powered self-healing and incident remediation testbed for cloud-native applications, operating locally with simulated telemetry and designed for future integration with the FlightWatch aviation monitoring platform.

---

## 1. Research Foundation

This project is grounded in the research paper:
> **"Integrating Large Language Models with Cloud-Native Observability for Automated Root Cause Analysis and Remediation"**

The research workflow implemented across this repository follows:
$$\text{Telemetry Ingestion} \longrightarrow \text{Feature Extraction \& Detection} \longrightarrow \text{LLM-Enhanced RCA} \longrightarrow \text{Policy-Governed Remediation} \longrightarrow \text{Post-Action Verification}$$

### System Separation Note
This repository is the independent **Final-Year Project (AI Self-Healing Engine)**. It runs completely locally on simulated telemetry without dependencies on cloud infrastructure or AWS credentials. The external **FlightWatch** production platform (React, Node.js/Express, PostgreSQL, Docker, AWS EC2/RDS, OpenTelemetry) will serve as a future telemetry provider without requiring architectural rewrites to this AI engine.

---

## 2. End-to-End Pipeline Architecture

```text
                       [ Deterministic Telemetry Simulator ]
                                         │
                             (Metrics, Logs, Spans)
                                         ▼
                     [ Telemetry Ingestion Interface / Buffer ]
                       (Sliding Window, OTel-Ready Schema)
                                         │
                                         ▼
                             [ Anomaly Detection Layer ]
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
           [ Statistical Z-Score ]                 [ ML Isolation Forest ]
           (Single-metric baseline)                (Multivariate feature vector)
                     └───────────────────┬───────────────────┘
                                         ▼
                            [ Structured Anomaly Event ]
                                         │
                                         ▼
                              [ Context Retrieval ]
           (Targeted log ranking, slow trace isolation, metric variance)
                                         │
                                         ▼
                         [ LLM Root Cause Analysis (RCA) ]
             ┌───────────────────────────┴───────────────────────────┐
             ▼                                                       ▼
   [ Real LLMs: OpenAI / Gemini ]                        [ Heuristic Mock Mode ]
   (Prompt injection defense, JSON schema)               (Offline deterministic fallback)
             └───────────────────────────┬───────────────────────────┘
                                         ▼
                        [ Structured Incident Diagnosis ]
                                         │
                                         ▼
                        [ Remediation Policy Engine ]
           (Allowlist check, shell-injection guard, anti-flapping loop protection)
                                         │
                                         ▼
                         [ Simulated Action Executor ]
             (restart_service, reset_db_pool, clear_memory_leak, etc.)
                                         │
                                         ▼
                       [ Post-Action Recovery Verifier ]
           (Telemetry delta check, metric normalization, active error audit)
                                         │
                                         ▼
                         [ Persistent Incident Reporter ]
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
           [ Canonical JSON Report ]               [ Human-Readable Markdown ]
             (reports/{ID}.json)                     (reports/{ID}.md)
```

---

## 3. Supported Failure Scenarios

The simulator provides deterministic, seedable telemetry across 6 distinct operational scenarios:

| ID | Scenario | Injected Fault | Primary Symptoms | Ground-Truth Remediation |
|---|---|---|---|---|
| **SCEN-00** | `NORMAL_OPERATION` | None (nominal) | Latency ~95ms, Error rate ~0.5%, CPU ~25%, DB ~14 | None |
| **SCEN-01** | `HIGH_LATENCY` | Unindexed database join | Latency > 3000ms, DB slow query logs, slow traces | `reduce_simulated_load` |
| **SCEN-02** | `ELEVATED_HTTP_ERROR_RATE` | Radar controller null pointer | HTTP 500 errors > 50%, unhandled exception logs | `restart_service` |
| **SCEN-03** | `DATABASE_CONNECTION_FAILURE` | Connection handle leak | DB connection saturation (100/100), pool timeouts, 503 errors | `reset_database_connection_pool` |
| **SCEN-04** | `CPU_MEMORY_PRESSURE` | Unbounded cache leak | Memory > 90%, CPU thrashing > 90%, GC pause logs | `clear_memory_leak` |
| **SCEN-05** | `CASCADING_FAILURE` | Compound buffer saturation | Memory leak -> DB starvation -> Cascading HTTP 500s | `restart_service` |

---

## 4. Repository Structure

```text
FlightWatch-AI-Self-Healing/
├── app/
│   └── dashboard.py               # Streamlit interactive web dashboard
├── experiments/
│   ├── evaluate.py                # Repeatable empirical evaluation benchmark
│   └── benchmark_results.json     # Measured empirical benchmark results
├── reports/                       # Persisted incident reports (.json and .md)
├── src/
│   ├── config.py                  # Settings, allowlists, and thresholds
│   ├── context/
│   │   ├── models.py              # IncidentContext data model
│   │   └── retriever.py           # Signal-ranked log & trace context retriever
│   ├── detection/
│   │   ├── base.py                # Abstract detector interface
│   │   ├── models.py              # Structured AnomalyEvent model
│   │   ├── statistical.py         # Statistical Z-Score detector (enhanced baseline)
│   │   └── ml_detector.py         # Scikit-Learn Isolation Forest detector
│   ├── incidents/
│   │   ├── models.py              # IncidentReport schema
│   │   └── reporter.py            # JSON and Markdown report generator
│   ├── orchestrator/
│   │   ├── pipeline.py            # End-to-end SelfHealingPipeline coordinator
│   │   └── verifier.py            # Post-action verification and metric comparison
│   ├── rca/
│   │   ├── analyzer.py            # RCA engine (OpenAI, Gemini, and Mock fallback)
│   │   ├── models.py              # Structured RCADiagnosis schema
│   │   └── prompt.py              # Prompt injection defense & schema builder
│   ├── remediation/
│   │   ├── actions.py             # Action definitions and risk metadata
│   │   ├── executor.py            # Simulator remediation executor
│   │   └── policy.py              # Policy engine (allowlist, anti-flapping guard)
│   └── telemetry/
│       ├── ingestion.py           # TelemetryIngestionBuffer (OTel-compatible)
│       ├── models.py              # TelemetryPoint, LogEntry, TraceSpan, GroundTruth
│       └── simulator.py           # Stateful, seedable telemetry simulator
├── tests/
│   ├── conftest.py                # Pytest discovery configuration
│   ├── test_context.py            # Context retriever unit tests
│   ├── test_detectors.py          # Statistical & ML detector unit tests
│   ├── test_end_to_end.py         # End-to-end pipeline integration tests
│   ├── test_rca.py                # RCA prompt defense and diagnosis tests
│   ├── test_remediation.py        # Policy engine allowlists & loop protection tests
│   └── test_simulator.py          # Telemetry simulator unit tests
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules
├── main.py                        # Command line interface (CLI)
├── pytest.ini                     # Pytest settings
├── requirements.txt               # Python package dependencies
└── README.md                      # Comprehensive documentation
```

---

## 5. Quick Start & Execution

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Windows / macOS / Linux

### 1. Installation
Clone or navigate to the repository directory and activate the virtual environment:
```powershell
# Windows
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` (optional; defaults to offline mock mode):
```powershell
cp .env.example .env
```
To enable live LLM diagnosis, configure `LLM_PROVIDER=openai` or `LLM_PROVIDER=gemini` with your respective API key in `.env`. If no key is provided, the system executes automatically in **Clearly Labeled Mock Mode**.

### 3. Run via Command Line Interface (CLI)
Run an automated end-to-end self-healing flow on any scenario:
```powershell
# Run cascading failure incident
python main.py --scenario CASCADING_FAILURE

# Run database connection failure incident
python main.py --scenario DATABASE_CONNECTION_FAILURE

# Run high latency incident with statistical detector only
python main.py --scenario HIGH_LATENCY --detector statistical

# List generated reports
python main.py --list-reports
```

### 4. Run the Streamlit Interactive Dashboard
Launch the web interface:
```powershell
streamlit run app/dashboard.py
```
Open `http://localhost:8501` in your browser to interactively trigger scenarios, monitor telemetry streams, inspect LLM diagnoses, and verify recoveries in real-time.

### 5. Run the Automated Test Suite
Execute all 22 unit and end-to-end integration tests:
```powershell
pytest -v
```

---

## 6. Empirical Experimental Evaluation

The evaluation framework (`experiments/evaluate.py`) empirically measures detection performance, diagnostic accuracy, and remediation effectiveness across all 6 scenarios with 5 trials per scenario (30 test runs):

```powershell
python experiments/evaluate.py
```

### Measured Benchmark Results

| Metric | Statistical Z-Score Detector | Isolation Forest Detector |
|---|---|---|
| **Precision** | **96.15%** | **96.15%** |
| **Recall** | **100.00%** | **100.00%** |
| **F1-Score** | **0.9804** | **0.9804** |
| **True Positives (TP)** | 25 | 25 |
| **False Positives (FP)** | 1 | 1 |
| **True Negatives (TN)** | 4 | 4 |
| **False Negatives (FN)** | 0 | 0 |

### Pipeline Diagnostic & Remediation Performance

| Evaluation Metric | Measured Result | Notes |
|---|---|---|
| **RCA Ground-Truth Diagnostic Accuracy** | **100.00%** (25/25) | Diagnosed root cause matched hidden ground truth label |
| **Remediation Recovery Success Rate** | **100.00%** (25/25) | Post-action telemetry returned within baseline bounds ($Z < 2.5$) |
| **Mean Pipeline Latency** | **0.0286 seconds** | End-to-end execution time from detection to verification |

*Full benchmark JSON is saved in `experiments/benchmark_results.json`.*

---

## 7. Safety, Security & Prompt Injection Defense

1. **Prompt Injection Guard:** All raw log lines, stack traces, and span attributes are isolated inside `<untrusted_telemetry_data>` XML blocks. Strict system instructions direct the LLM to ignore any instructions, scripts, or directives embedded inside log bodies.
2. **Strict Action Allowlist:** The orchestrator only executes actions explicitly registered in `settings.ALLOWED_ACTIONS`:
   - `restart_service`
   - `reset_database_connection_pool`
   - `clear_memory_leak`
   - `reduce_simulated_load`
   - `rollback_configuration`
3. **Shell Command Blocker:** Rejects shell characters (`;`, `&&`, `|`, `rm`, `sudo`) before action execution.
4. **Anti-Flapping & Loop Protection:** The policy engine enforces a maximum retry ceiling per service window (`MAX_REMEDIATION_RETRIES=2`), preventing infinite restart loops and escalating recurring failures to human SREs.

---

## 8. Limitations & Future FlightWatch Cloud Integration

1. **Synthetic Telemetry vs. Production Realities:** While the deterministic telemetry generator reproduces realistic failure dynamics (slow query latencies, pool starvation, null pointers, cascading memory exhaustion), it lacks real-world production noise, multi-tenant network jitter, and long-tail metric drift. High benchmark scores in synthetic environments do not guarantee identical zero-shot accuracy on live production traffic.
2. **Stateless vs. Stateful Workloads:** Simulated restarts seamlessly restore health. In stateful cloud production services, restarts may cause cache eviction, connection re-establishment thundering herds, or partial data synchronization delays.
3. **Future FlightWatch OpenTelemetry Integration:**
   - The `TelemetryIngestionBuffer` was architected with OpenTelemetry data types (`TelemetryPoint`, `LogEntry`, `TraceSpan`).
   - In the next phase, an OpenTelemetry Collector HTTP receiver endpoint will feed live OTEL metric/log/trace JSON payloads directly into `TelemetryIngestionBuffer.ingest_batch()` without altering the downstream detection, RCA, policy, or verification components.
