"""Action definitions and metadata for remediation operations."""
from enum import Enum
from typing import Dict, Any

class ActionType(str, Enum):
    RESTART_SERVICE = "restart_service"
    RESET_DATABASE_CONNECTION_POOL = "reset_database_connection_pool"
    CLEAR_MEMORY_LEAK = "clear_memory_leak"
    REDUCE_SIMULATED_LOAD = "reduce_simulated_load"
    ROLLBACK_CONFIGURATION = "rollback_configuration"

ACTION_METADATA: Dict[str, Dict[str, Any]] = {
    ActionType.RESTART_SERVICE.value: {
        "description": "Performs graceful worker restart of the simulated service",
        "risk_level": "MEDIUM",
        "expected_duration_seconds": 1.5,
        "preconditions": ["service_registered"],
    },
    ActionType.RESET_DATABASE_CONNECTION_POOL.value: {
        "description": "Drains and re-initializes database client pool connections",
        "risk_level": "LOW",
        "expected_duration_seconds": 0.5,
        "preconditions": ["db_configured"],
    },
    ActionType.CLEAR_MEMORY_LEAK.value: {
        "description": "Flushes unbounded in-memory caches and forces garbage collection",
        "risk_level": "LOW",
        "expected_duration_seconds": 0.8,
        "preconditions": ["service_registered"],
    },
    ActionType.REDUCE_SIMULATED_LOAD.value: {
        "description": "Enables temporary rate limiting to shed excess traffic",
        "risk_level": "LOW",
        "expected_duration_seconds": 0.2,
        "preconditions": ["rate_limiter_active"],
    },
    ActionType.ROLLBACK_CONFIGURATION.value: {
        "description": "Reverts recent config parameter changes to previous stable release",
        "risk_level": "MEDIUM",
        "expected_duration_seconds": 1.0,
        "preconditions": ["previous_config_present"],
    },
}
