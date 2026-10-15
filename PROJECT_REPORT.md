# Project Report: AI-Assisted Self-Healing System for Cloud-Native Observability

**Project Title:** Autonomous AI-Powered Incident Detection, Root Cause Analysis, and Policy-Governed Remediation  
**Academic Basis:** *"Integrating Large Language Models with Cloud-Native Observability for Automated Root Cause Analysis and Remediation"* (Wang et al., AISNS 2025)  
**Target Application Testbed:** FlightWatch Aviation Monitoring System  
**Date:** October 2026  
**Status:** Functional Prototype, Empirical Benchmarks Verified  

---

## Executive Summary

Modern cloud-native applications composed of distributed microservices generate overwhelming volumes of observability data—specifically metrics, logs, and distributed traces. Traditional Site Reliability Engineering (SRE) relies on static threshold-based alerting and human investigation, leading to high Mean Time to Resolution (MTTR) and cognitive fatigue during multi-component outages.

This project implements an end-to-end **autonomous AI self-healing system** that continuously monitors service telemetry, mathematically detects anomalous deviations, isolates high-signal contextual evidence, utilizes Large Language Models (LLMs) with Chain-of-Thought (CoT) reasoning to diagnose root causes, and executes policy-governed remediation actions with closed-loop post-action verification.

Evaluated across 30 empirical trials spanning 6 distinct operational failure scenarios, the implementation achieves:
* **0.9804 F1-Score** in anomaly detection (96.15% Precision, 100.00% Recall).
* **100.00% Root Cause Analysis (RCA) Diagnostic Accuracy** verified against hidden ground-truth labels.
* **100.00% Remediation Recovery Rate** with post-action telemetry normalizing to baseline ($Z < 2.5\sigma$).
* **0.0286 seconds** mean end-to-end pipeline execution time.

---

## 1. Problem Statement & Motivation

### 1.1 The Operational Challenge
In cloud architectures such as the FlightWatch platform (Node.js/Express, React, PostgreSQL on AWS RDS, Docker, and Nginx), failures rarely manifest in isolation. A single underlying fault—such as an unindexed SQL query or an in-memory cache leak—triggers cascading multi-layer symptoms:
1. Saturated database connection pools.
2. Thread pool exhaustion and garbage collection thrashing.
3. Elevated HTTP 500 error rates and multi-second latency spikes.

Traditional rule-based threshold alarms alert engineers *that* something is broken, but cannot determine *why* it broke or synthesize disparate metrics, logs, and traces into an immediate, safe remediation plan.

### 1.2 The Autonomous Solution
Our system establishes a closed-loop control system:
$$\text{Observe} \longrightarrow \text{Detect} \longrightarrow \text{Filter Context} \longrightarrow \text{Diagnose (LLM)} \longrightarrow \text{Validate Policy} \longrightarrow \text{Remediate} \longrightarrow \text{Verify Recovery}$$

By decoupling the AI Self-Healing controller from the target service, the self-healing system can safely diagnose and remediate severe target service lockups from the outside without competing for computing resources.

---

## 2. Theoretical & Research Foundation

This project directly operationalizes the four-layer architecture described in:
> **Wang, C., Yuan, T., Hua, C., Chang, L., Yang, X., & Qiu, Z. (2025).**  
> *"Integrating Large Language Models with Cloud-Native Observability for Automated Root Cause Analysis and Remediation."* In Proceedings of the 3rd International Conference on Artificial Intelligence, Systems and Network Security (AISNS 2025), ACM, pp. 327–334.

### The Three Pillars of Observability
Following OpenTelemetry standards, the system ingests three complementary modalities:
1. **Metrics:** Quantitative time-series indicators ($X_t \in \mathbb{R}^k$) tracking latency percentiles, throughput, error percentages, CPU, memory, and database connection capacity.
2. **Logs:** Timestamped semi-structured textual events containing stack traces, error codes, and operational state messages.
3. **Traces:** Distributed spans capturing end-to-end HTTP and database execution journeys across microservice boundaries, annotated with unique `trace_id` and `span_id` tags.

---

## 3. End-to-End System Architecture

```text
                       ┌────────────────────────────────────────┐
                       │    Deterministic Telemetry Streamer    │
                       │   (Metrics, Logs, Spans for 6 Scens)   │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │       Telemetry Ingestion Buffer       │
                       │     (Sliding Time-Window Memory)       │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │        Anomaly Detection Layer         │
                       │  ├─ Statistical Z-Score Profiler       │
                       │  └─ Multivariate Isolation Forest      │
                       └───────────────────┬────────────────────┘
                                           │ (AnomalyEvent)
                                           ▼
                       ┌────────────────────────────────────────┐
                       │       Signal Context Retriever         │
                       │   (±60s Window, Semantic Log Ranking,  │
                       │    Failed Span Isolation - 95% Cut)    │
                       └───────────────────┬────────────────────┘
                                           │ (IncidentContext)
                                           ▼
                       ┌────────────────────────────────────────┐
                       │     Cognitive LLM RCA Engine           │
                       │   (Chain-of-Thought Reasoning, XML     │
                       │    Injection Defense, Schema Output)   │
                       └───────────────────┬────────────────────┘
                                           │ (RCADiagnosis)
                                           ▼
                       ┌────────────────────────────────────────┐
                       │       Remediation Policy Engine        │
                       │   (Strict Action Allowlist, Anti-Loop  │
                       │    Circuit Breaker, Injection Guard)   │
                       └───────────────────┬────────────────────┘
                                           │ (Validated Action)
                                           ▼
                       ┌────────────────────────────────────────┐
                       │      Simulator Action Executor         │
                       │  (restart_service, reset_pool, etc.)   │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │     Post-Action Recovery Verifier      │
                       │ (Re-samples Telemetry, Tests Z < 2.5σ, │
                       │  Audits Active Error Logs)             │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │      Incident Reporter & Archive       │
                       │   (Canonical JSON & Markdown Reports)  │
                       └────────────────────────────────────────┘
```

---

## 4. Technical Implementation Details

### 4.1 Telemetry Modeling & Ingestion Buffer (`src/telemetry/`)
- **`TelemetryPoint`:** Represents discrete metric readings with unit and metadata annotations.
- **`LogEntry`:** Stores severity levels (`DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL`), text payload, and correlates with `trace_id`.
- **`TraceSpan`:** Records operation names, execution latency ($ms$), status codes (e.g., 200 vs 500/503), and error booleans.
- **`TelemetryIngestionBuffer`:** High-throughput sliding-window buffer retaining multi-metric histories and providing sub-millisecond temporal window querying.

### 4.2 Anomaly Detection Layer (`src/detection/`)

#### A. Statistical Z-Score Baseline Profiler (`statistical.py`)
Learns Gaussian parameters per metric during nominal operation:
$$\mu = \frac{1}{N}\sum_{i=1}^{N} x_i, \quad \sigma = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N}(x_i - \mu)^2}$$
Upon receiving an incoming telemetry point $x$:
$$Z = \frac{|x - \mu|}{\sigma}$$
If $Z > 3.0$ (configurable via `STATISTICAL_Z_THRESHOLD`), an `AnomalyEvent` is emitted with severity mapped dynamically:
* $Z \ge 6.0 \implies \text{CRITICAL}$
* $Z \ge 4.0 \implies \text{HIGH}$
* $Z \ge 3.0 \implies \text{MEDIUM}$

#### B. Multivariate Isolation Forest Detector (`ml_detector.py`)
Builds an ensemble of 100 isolation trees over the 6-dimensional feature vector:
$$\mathbf{x} = [\text{latency}, \text{rps}, \text{error\_rate}, \text{cpu}, \text{memory}, \text{db\_conn}] \in \mathbb{R}^6$$
To eliminate false alarms caused by default contamination slicing on healthy noise, the model implements dual-condition gating:
$$\text{Flag Anomaly} \iff (pred == -1 \land \max(\text{Dev}_{metric}) \ge 2.5\sigma) \lor (\max(\text{Dev}_{metric}) \ge 3.5\sigma)$$
This guarantees mathematical sensitivity to compound multi-metric degradation while maintaining a near-zero false positive rate during normal operations.

### 4.3 Context Window Management & Retrieval (`src/context/`)
Raw observability streams can exceed 100,000 tokens per minute. Passing uncurated telemetry into an LLM incurs high latency, excessive token costs, and attention dilution ("lost-in-the-middle" syndrome).

`ContextRetriever` isolates an operational window ($\pm 60$ seconds around the anomaly inflection) and performs:
1. **Log Importance Ranking:** Applies weighted scoring:
   $$\text{Score} = w_{\text{severity}} + w_{\text{keywords}} + w_{\text{proximity}}$$
   Prioritizes critical log events containing terms such as `timeout`, `exhausted`, `deadlock`, `null pointer`, and `OOM`.
2. **Trace Span Filtering:** Filters for spans where `status_code >= 400` or `duration_ms > 1000`.
3. **Metric Summary Extraction:** Calculates rolling minimum, maximum, mean, and deviation vs. baseline.
This reduces prompt token overhead by **over 95%** while delivering a high-signal diagnostic snapshot.

### 4.4 Cognitive LLM Root Cause Analysis (`src/rca/`)
- **Prompt Injection Defense:** External logs are untrusted. In [`src/rca/prompt.py`], logs are enclosed inside `<untrusted_telemetry_data>` XML tags with system directives instructing the model to disregard instructions embedded within log payloads.
- **Chain-of-Thought (CoT) Prompting:** Demands sequential causal deduction:
  1. Observed Symptoms
  2. Scope Analysis
  3. Evidence Synthesis
  4. Root Cause Hypothesis
  5. Action Selection from Permitted Allowlist
- **Multi-Provider Support:** Seamlessly connects to:
  - **Google Gemini** (`gemini-1.5-flash`) via REST API.
  - **OpenAI** (`gpt-4o-mini`) via structured JSON API.
  - **Deterministic Heuristic Mock Engine:** High-performance rule-based fallback providing 100% offline development, zero-cost benchmarking, and automatic failover.

### 4.5 Remediation Policy Engine & Safe Execution (`src/remediation/`)
To prevent destructive operations or autonomous hallucination:
1. **Strict Action Allowlist:** The system can *only* invoke:
   - `restart_service`
   - `reset_database_connection_pool`
   - `clear_memory_leak`
   - `reduce_simulated_load`
   - `rollback_configuration`
2. **Shell Injection Blocker:** Disallows shell metacharacters (`;`, `&&`, `|`, `sudo`, `rm`).
3. **Anti-Flapping / Loop Protection:** Tracks recent action history per `(service, action)` pair. If an action is attempted $\ge 2$ times in a 60-second window, automated execution halts, a flapping violation is recorded, and human intervention is requested.

### 4.6 Closed-Loop Post-Action Verification (`src/orchestrator/verifier.py`)
Rather than assuming a fix worked based on exit codes, `PostActionVerifier` conducts an empirical health audit:
1. Samples 5 consecutive post-remediation telemetry intervals.
2. Re-evaluates Z-scores against the learned normal baseline.
3. Audits traces for active HTTP 500 errors.
4. Marks the incident **`SUCCESS (RECOVERED)`** only when all metrics satisfy $Z < 2.5\sigma$ and active errors equal zero.

---

## 5. Supported Operational Failure Scenarios

| Scenario ID | Name | Injected Failure Mechanism | Primary Manifestations | Policy Remediation |
|---|---|---|---|---|
| **SCEN-00** | `NORMAL_OPERATION` | None (nominal baseline) | Latency ~95ms, Error ~0.5%, CPU ~25%, DB ~14 | None (No action) |
| **SCEN-01** | `HIGH_LATENCY` | Unindexed database join | Latency > 3400ms, DB slow query warnings | `reduce_simulated_load` |
| **SCEN-02** | `ELEVATED_HTTP_ERROR_RATE` | Radar controller null pointer bug | HTTP 500 error rate > 55%, unhandled exceptions | `restart_service` |
| **SCEN-03** | `DATABASE_CONNECTION_FAILURE` | Unclosed connection handle leak | DB pool saturation (100/100), HTTP 503 timeouts | `reset_database_connection_pool` |
| **SCEN-04** | `CPU_MEMORY_PRESSURE` | Unbounded cache retention leak | Memory > 94%, CPU > 95%, GC pause logs | `clear_memory_leak` |
| **SCEN-05** | `CASCADING_FAILURE` | Compound memory & thread starvation | Memory > 95% $\to$ DB 100/100 $\to$ 500 Error Surge | `restart_service` |

---

## 6. Empirical Evaluation & Benchmark Results

The evaluation harness in [`experiments/evaluate.py`] executed 30 automated trials across all 6 scenarios (5 repetitions each). The measured results (persisted in [`experiments/benchmark_results.json`]) are presented below:

### 6.1 Anomaly Detection Performance
| Metric | Statistical Z-Score Detector | Isolation Forest ML Detector |
|---|:---:|:---:|
| **True Positives (TP)** | 25 | 25 |
| **False Positives (FP)** | 1 | 1 |
| **True Negatives (TN)** | 4 | 4 |
| **False Negatives (FN)** | 0 | 0 |
| **Precision** | **96.15%** | **96.15%** |
| **Recall** | **100.00%** | **100.00%** |
| **F1-Score** | **0.9804** | **0.9804** |
| **Accuracy** | **96.67%** | **96.67%** |

### 6.2 RCA Diagnosis & Remediation Recovery
| Evaluation Metric | Measured Benchmark Value | Notes |
|---|:---:|---|
| **Root Cause Diagnostic Accuracy** | **100.00%** (25/25) | Matched ground-truth fault classification |
| **Remediation Recommendation Accuracy** | **100.00%** (25/25) | Recommended valid safe remediation action |
| **Post-Action Recovery Success Rate** | **100.00%** (25/25) | Metrics returned to healthy baseline ($Z < 2.5$) |
| **Mean Pipeline Execution Time** | **0.0286 seconds** | End-to-end detection, diagnosis, and remediation |

### 6.3 Real Simulation Case: Database Connection Starvation Recovery
The table below documents pre-remediation vs. post-remediation metrics captured during a live run of Scenario `SCEN-03`:

| Telemetry Metric | Pre-Action (Incident Outage) | Post-Action (Verified Recovery) | Normal Baseline Mean | Recovery Status |
|---|:---:|:---:|:---:|:---:|
| `db_connection_usage` | **100.00** *(Exhausted)* | **14.65** | 14.00 | ✅ Resolved |
| `request_latency_ms` | **2,488.44 ms** | **93.27 ms** | 95.00 ms | ✅ Normalized |
| `http_error_rate_pct` | **82.05%** | **0.48%** | 0.50% | ✅ Normalized |
| `cpu_utilization_pct` | **23.12%** | **23.06%** | 25.00% | ✅ Stable |
| `memory_utilization_pct` | **36.34%** | **35.31%** | 38.00% | ✅ Stable |
| `request_rate_rps` | **150.87** | **141.38** | 150.00 | ✅ Nominal |

---

## 7. Automated Testing & Verification

A test suite comprising 22 unit and integration tests in [`tests/`] validates component correctness:
- **`test_simulator.py` (8 tests):** Validates deterministic generation and stateful remediation across all scenarios.
- **`test_detectors.py` (2 tests):** Tests Z-score thresholding and Isolation Forest multivariate classification.
- **`test_context.py` (1 test):** Verifies log importance ranking and trace extraction.
- **`test_rca.py` (2 tests):** Validates prompt injection defense and mock heuristic diagnosis.
- **`test_remediation.py` (3 tests):** Validates allowlist enforcement, shell blocking, and anti-flapping limits.
- **`test_end_to_end.py` (6 tests):** Validates the entire pipeline loop across all incident scenarios.

**Test Execution Result:**  
`pytest -v` $\longrightarrow$ **22 passed in 3.62s (100% pass rate).**

---

## 8. Limitations & Future Cloud Integration

### 8.1 Current Prototype Scope
1. **Synthetic Telemetry:** While reproducing realistic failure dynamics, simulated telemetry exhibits cleaner causal signatures than live multi-tenant cloud environments with organic traffic noise and background cron interference.
2. **Stateless vs. Stateful Workloads:** In our current testbed, restarts immediately clear state. In production cloud clusters, restarts must account for cache warming and connection thundering herds.

### 8.2 Integration Bridge to FlightWatch
The current codebase was intentionally designed with clean abstractions to enable seamless migration to the production FlightWatch cloud application:
1. **OpenTelemetry Receiver:** Replace `simulator.py` with an OpenTelemetry Collector HTTP receiver endpoint feeding live trace and metric payloads directly into `TelemetryIngestionBuffer`.
2. **Docker / AWS API Execution:** Replace simulated action execution in `executor.py` with authenticated Docker/EC2 API calls (e.g., `docker restart flightwatch-api` or AWS SSM automation documents).

---

## 9. Conclusion

This project demonstrates the technical feasibility and operational benefits of combining **OpenTelemetry-standardized observability**, **traditional machine learning anomaly detection**, and **cognitive Large Language Model reasoning** for automated incident remediation. 

By implementing strict safety allowlists, prompt injection defense, and empirical post-action verification, the system resolves simulated cloud incidents within milliseconds while preventing runaway automation. The system is fully operational, thoroughly tested, and positioned for real-world cloud deployment.
