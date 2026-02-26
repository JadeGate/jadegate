"""
JadeGate Circuit Breaker — Automatic fault isolation.

When a tool fails repeatedly, the circuit breaker trips and blocks
further calls until a cooldown period passes. Prevents cascading failures.
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Dict

logger = logging.getLogger("jadegate.runtime.circuit_breaker")


class BreakerState(str, Enum):
    CLOSED = "closed"        # Normal, calls pass through
    OPEN = "open"            # Tripped, all calls blocked
    HALF_OPEN = "half_open"  # Testing recovery, one call allowed


class CircuitBreaker:
    """
    Circuit breaker manager for all tools.

    Each tool gets its own breaker. When a tool fails `threshold` times
    consecutively, its breaker opens and blocks calls for `timeout_sec`.
    After timeout, it enters half-open state and allows one probe call.
    """

    def __init__(self, threshold: int = 5, timeout_sec: float = 60.0):
        self._threshold = threshold
        self._timeout_sec = timeout_sec
        # Per-tool state: {tool_name: {state, failure_count, success_count, last_failure, trip_count}}
        self._state: Dict[str, Dict] = {}

    def _get(self, tool_name: str) -> Dict:
        if tool_name not in self._state:
            self._state[tool_name] = {
                "state": BreakerState.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0.0,
                "trip_count": 0,
            }
        return self._state[tool_name]

    def can_call(self, tool_name: str) -> bool:
        """Check if a tool call is allowed."""
        s = self._get(tool_name)

        if s["state"] == BreakerState.CLOSED:
            return True

        if s["state"] == BreakerState.OPEN:
            elapsed = time.time() - s["last_failure_time"]
            if elapsed >= self._timeout_sec:
                s["state"] = BreakerState.HALF_OPEN
                logger.info("Circuit breaker for '%s' → HALF_OPEN (probe allowed)", tool_name)
                return True
            return False

        # HALF_OPEN: allow one probe
        return True

    def record_success(self, tool_name: str) -> None:
        """Record a successful call. Resets breaker if half-open."""
        s = self._get(tool_name)
        s["success_count"] += 1

        if s["state"] == BreakerState.HALF_OPEN:
            s["state"] = BreakerState.CLOSED
            s["failure_count"] = 0
            logger.info("Circuit breaker for '%s' → CLOSED (recovered)", tool_name)
        elif s["state"] == BreakerState.CLOSED:
            s["failure_count"] = 0

    def record_failure(self, tool_name: str) -> bool:
        """Record a failed call. Returns True if the breaker just tripped."""
        s = self._get(tool_name)
        s["failure_count"] += 1
        s["last_failure_time"] = time.time()

        if s["state"] == BreakerState.HALF_OPEN:
            s["state"] = BreakerState.OPEN
            s["trip_count"] += 1
            logger.warning("Circuit breaker for '%s' → OPEN (probe failed)", tool_name)
            return True

        if s["state"] == BreakerState.CLOSED and s["failure_count"] >= self._threshold:
            s["state"] = BreakerState.OPEN
            s["trip_count"] += 1
            logger.warning(
                "Circuit breaker for '%s' → OPEN (%d consecutive failures)",
                tool_name, s["failure_count"],
            )
            return True

        return False

    def reset(self, tool_name: str) -> None:
        """Manually reset a breaker."""
        if tool_name in self._state:
            del self._state[tool_name]
            logger.info("Circuit breaker for '%s' manually reset", tool_name)

    def reset_all(self) -> None:
        """Reset all breakers."""
        self._state.clear()

    def get_status(self) -> Dict[str, Dict]:
        """Get status of all breakers."""
        result = {}
        for name, s in self._state.items():
            # Auto-check open→half_open transition
            if s["state"] == BreakerState.OPEN:
                elapsed = time.time() - s["last_failure_time"]
                if elapsed >= self._timeout_sec:
                    s["state"] = BreakerState.HALF_OPEN

            result[name] = {
                "state": s["state"].value if isinstance(s["state"], BreakerState) else s["state"],
                "failure_count": s["failure_count"],
                "success_count": s["success_count"],
                "trip_count": s["trip_count"],
            }
        return result
