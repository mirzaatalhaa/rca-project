"""Remediation Policy Engine.
Validates LLM recommendations against strict security allowlists,
precondition checks, and flapping/loop prevention.
"""
import time
from typing import Tuple, Dict, List
from collections import defaultdict
from src.config import settings
from src.remediation.actions import ACTION_METADATA

class RemediationPolicyEngine:
    """Enforces safety policies, allowlists, and execution boundaries on remediation actions."""

    def __init__(self, max_retries: int = 2, loop_cooldown_seconds: float = 60.0):
        self.allowed_actions = set(settings.ALLOWED_ACTIONS)
        self.max_retries = max_retries
        self.loop_cooldown_seconds = loop_cooldown_seconds
        # History map: (service, action) -> list of execution timestamps
        self._action_history: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def validate(self, action: str, service: str) -> Tuple[bool, str]:
        """Validate an action for a given service against policies."""
        # 1. Reject empty or non-string actions
        if not action or not isinstance(action, str):
            return False, "REJECTED: Action is empty or invalid format."

        # 2. Security check: Reject shell command injection attempts
        dangerous_tokens = [";", "&&", "||", "|", "`", "$", ">", "<", "rm ", "sh ", "bash", "powershell", "sudo"]
        for token in dangerous_tokens:
            if token in action.lower():
                return False, f"SECURITY ALERT: Action contains forbidden characters or command execution tokens."

        # 3. Strict allowlist check
        clean_action = action.strip().lower()
        if clean_action not in self.allowed_actions:
            return False, f"REJECTED: Action '{action}' is not in policy allowlist. Allowed: {list(self.allowed_actions)}"

        # 4. Service validity check
        if not service or len(service) < 2:
            return False, "REJECTED: Target service is missing or malformed."

        # 5. Remediation loop / flapping protection
        now = time.time()
        key = (service, clean_action)
        recent_timestamps = [
            ts for ts in self._action_history[key]
            if (now - ts) < self.loop_cooldown_seconds
        ]
        self._action_history[key] = recent_timestamps

        if len(recent_timestamps) >= self.max_retries:
            return False, (
                f"REJECTED: Repeated remediation loop detected. Action '{clean_action}' has already "
                f"been executed {len(recent_timestamps)} times for service '{service}' in the last "
                f"{self.loop_cooldown_seconds}s. Escalating to human SRE."
            )

        return True, "PASSED: Action validated against security allowlist and policy limits."

    def record_execution(self, service: str, action: str) -> None:
        """Record an executed action for loop detection tracking."""
        key = (service, action.strip().lower())
        self._action_history[key].append(time.time())

    def reset_history(self) -> None:
        """Reset historical loop counters (useful for unit testing)."""
        self._action_history.clear()
