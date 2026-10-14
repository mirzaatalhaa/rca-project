"""Configuration management for AI-Powered Self-Healing System."""
import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    BASE_DIR: Path = BASE_DIR
    REPORTS_DIR: Path = REPORTS_DIR

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock").lower()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Detection Thresholds
    STATISTICAL_Z_THRESHOLD: float = float(os.getenv("STATISTICAL_Z_THRESHOLD", "3.0"))
    ISOLATION_FOREST_CONTAMINATION: float = float(os.getenv("ISOLATION_FOREST_CONTAMINATION", "0.08"))

    # Remediation Policy Settings
    ALLOWED_ACTIONS: List[str] = [
        "restart_service",
        "reset_database_connection_pool",
        "clear_memory_leak",
        "reduce_simulated_load",
        "rollback_configuration",
    ]
    
    ACTION_TIMEOUT_SECONDS: int = int(os.getenv("REMEDIATION_TIMEOUT_SECONDS", "10"))
    MAX_REMEDIATION_RETRIES: int = int(os.getenv("MAX_REMEDIATION_RETRIES", "2"))
    AUTO_REMEDIATE: bool = os.getenv("AUTO_REMEDIATE", "true").lower() in ("true", "1", "yes")

    # Telemetry metrics tracked
    TRACKED_METRICS: List[str] = [
        "request_latency_ms",
        "request_rate_rps",
        "http_error_rate_pct",
        "cpu_utilization_pct",
        "memory_utilization_pct",
        "db_connection_usage",
    ]

settings = Settings()
