"""
JadeGate Session — Security context for a single agent session.

A session ties together policy, runtime DAG, interceptor, and circuit breaker.
One session per agent conversation / MCP connection.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from ..policy.policy import JadePolicy
from .dynamic_dag import DynamicDAG, Anomaly
from .circuit_breaker import CircuitBreaker

logger = logging.getLogger("jadegate.runtime.session")


class JadeSession:
    """
    A security session. One per agent conversation or MCP connection.

    Usage:
        session = JadeSession()
        result = session.before_call("file_read", {"path": "/tmp/data.txt"})
        if result.allowed:
            data = do_file_read("/tmp/data.txt")
            session.after_call(result.call_id, success=True)
        else:
            print(f"Blocked: {result.reasons}")
    """

    def __init__(
        self,
        policy: Optional[JadePolicy] = None,
        session_id: Optional[str] = None,
    ):
        self._session_id = session_id or str(uuid.uuid4())[:16]
        self._policy = policy or JadePolicy.default()
        self._dag = DynamicDAG(max_depth=self._policy.max_call_depth)
        self._breaker = CircuitBreaker(
            threshold=self._policy.circuit_breaker_threshold,
            timeout_sec=self._policy.circuit_breaker_timeout_sec,
        )
        # Lazy import to avoid circular dependency
        from .interceptor import ToolCallInterceptor
        self._interceptor = ToolCallInterceptor(
            policy=self._policy,
            dag=self._dag,
            circuit_breaker=self._breaker,
        )
        self._created_at = time.time()
        self._call_count = 0
        self._blocked_count = 0
        self._closed = False

        logger.info("JadeSession %s created", self._session_id)

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def policy(self) -> JadePolicy:
        return self._policy

    @property
    def dag(self) -> DynamicDAG:
        return self._dag

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._breaker

    @property
    def interceptor(self):
        return self._interceptor

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    @property
    def anomalies(self) -> List[Anomaly]:
        return self._dag.anomalies

    def before_call(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Evaluate a tool call before execution."""
        if self._closed:
            from .interceptor import InterceptResult, CallVerdict
            return InterceptResult(
                verdict=CallVerdict.DENY,
                call_id="closed",
                tool_name=tool_name,
                reasons=["Session is closed"],
                anomalies=[],
                risk_level="high",
            )

        params = params or {}
        result = self._interceptor.before_call(tool_name, params, context)
        self._call_count += 1

        if not result.allowed:
            self._blocked_count += 1

        return result

    def after_call(
        self,
        call_id: str,
        success: bool = True,
        error_message: str = "",
    ) -> None:
        """Report the result of a tool call after execution."""
        if not self._closed:
            self._interceptor.after_call(call_id, success, error_message)

    def get_status(self) -> Dict[str, Any]:
        """Get session status summary."""
        uptime = time.time() - self._created_at
        return {
            "session_id": self._session_id,
            "uptime_sec": round(uptime, 1),
            "policy": "custom" if self._policy != JadePolicy.default() else "default",
            "total_calls": self._call_count,
            "blocked_calls": self._blocked_count,
            "block_rate": round(self._blocked_count / max(self._call_count, 1), 3),
            "dag_depth": self._dag.depth,
            "anomalies": len(self._dag.anomalies),
            "circuit_breakers": self._breaker.get_status(),
            "closed": self._closed,
        }

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get the full audit log."""
        return self._interceptor.audit_log

    def close(self) -> Dict[str, Any]:
        """Close the session and return final status."""
        self._closed = True
        status = self.get_status()
        logger.info(
            "JadeSession %s closed: %d calls, %d blocked, %d anomalies",
            self._session_id, self._call_count, self._blocked_count,
            len(self._dag.anomalies),
        )
        return status
