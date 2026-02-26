"""
JadeGate Interceptor — The core gatekeeper for every tool call.

Every tool call passes through here. The interceptor:
1. Checks policy (blocked actions, permissions)
2. Scans parameters for dangerous patterns
3. Updates the dynamic DAG
4. Checks circuit breaker
5. Returns Allow / Deny / NeedApproval

All local. Zero network calls.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..policy.policy import JadePolicy
from .dynamic_dag import DynamicDAG, DAGNode, Anomaly, AnomalyType
from .circuit_breaker import CircuitBreaker

logger = logging.getLogger("jadegate.runtime.interceptor")

# Dangerous patterns (subset of jade_core SecurityEngine patterns)
_DANGEROUS_PATTERNS = [
    re.compile(r'\brm\s+-rf\b', re.I),
    re.compile(r'\bmkfs\b', re.I),
    re.compile(r'\bdd\s+if=', re.I),
    re.compile(r'\bchmod\s+777\b', re.I),
    re.compile(r'\beval\s*\(', re.I),
    re.compile(r'\bexec\s*\(', re.I),
    re.compile(r'\b__import__\s*\(', re.I),
    re.compile(r'\bos\.system\s*\(', re.I),
    re.compile(r'\bsubprocess\b', re.I),
    re.compile(r'curl\s+.*\|\s*(?:ba)?sh', re.I),
    re.compile(r'wget\s+.*\|\s*(?:ba)?sh', re.I),
    re.compile(r'>\s*/dev/sda', re.I),
    re.compile(r'\bshutdown\b', re.I),
    re.compile(r'\breboot\b', re.I),
    re.compile(r'\bkillall\b', re.I),
]

_SENSITIVE_FILE_PATTERNS = [
    "/etc/shadow", "/etc/passwd", ".ssh/id_", ".gnupg/",
    ".aws/credentials", ".config/gcloud",
]


class CallVerdict(str, Enum):
    """Result of interceptor evaluation."""
    ALLOW = "allow"
    DENY = "deny"
    NEED_APPROVAL = "need_approval"


@dataclass
class InterceptResult:
    """Full result of a tool call interception."""
    verdict: CallVerdict
    call_id: str
    tool_name: str
    reasons: List[str]
    anomalies: List[Anomaly]
    risk_level: str = "low"

    @property
    def allowed(self) -> bool:
        return self.verdict == CallVerdict.ALLOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "reasons": self.reasons,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "risk_level": self.risk_level,
        }


def _sanitize_params(params: Dict[str, Any], max_str_len: int = 200) -> Dict[str, Any]:
    """Create a sanitized summary of params for DAG storage."""
    sanitized = {}
    for k, v in params.items():
        if isinstance(v, str):
            sanitized[k] = v[:max_str_len] + "..." if len(v) > max_str_len else v
        elif isinstance(v, (int, float, bool)):
            sanitized[k] = v
        elif isinstance(v, list):
            sanitized[k] = f"[list, len={len(v)}]"
        elif isinstance(v, dict):
            sanitized[k] = f"{{dict, keys={list(v.keys())[:5]}}}"
        else:
            sanitized[k] = str(type(v).__name__)
    return sanitized


def _deep_string_scan(obj: Any, depth: int = 0) -> List[str]:
    """Extract all string values from a nested structure."""
    if depth > 10:
        return []
    strings = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            strings.extend(_deep_string_scan(v, depth + 1))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            strings.extend(_deep_string_scan(v, depth + 1))
    return strings


class ToolCallInterceptor:
    """
    The gatekeeper. Every tool call goes through here.

    Usage:
        interceptor = ToolCallInterceptor(policy, dag, breaker)
        result = interceptor.before_call("file_read", {"path": "/etc/passwd"})
        if result.allowed:
            # execute the call
            interceptor.after_call(result.call_id, success=True)
    """

    def __init__(
        self,
        policy: JadePolicy,
        dag: DynamicDAG,
        circuit_breaker: CircuitBreaker,
    ):
        self._policy = policy
        self._dag = dag
        self._breaker = circuit_breaker

        # Try to import jade_core SecurityEngine for enhanced scanning
        self._security_engine = None
        try:
            from jade_core.security import SecurityEngine
            self._security_engine = SecurityEngine()
            logger.debug("Loaded jade_core SecurityEngine for enhanced scanning")
        except ImportError:
            logger.debug("jade_core not available, using built-in pattern scan")

        self._audit_log: List[Dict[str, Any]] = []

    @property
    def audit_log(self) -> List[Dict[str, Any]]:
        return list(self._audit_log)

    def before_call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> InterceptResult:
        """Evaluate a tool call BEFORE execution."""
        call_id = str(uuid.uuid4())[:12]
        reasons: List[str] = []
        anomalies: List[Anomaly] = []
        risk_level = "low"
        verdict = CallVerdict.ALLOW

        # 1. Circuit breaker
        if not self._breaker.can_call(tool_name):
            reasons.append(f"Circuit breaker OPEN for '{tool_name}'")
            self._log_audit(call_id, tool_name, params, CallVerdict.DENY, reasons)
            return InterceptResult(
                verdict=CallVerdict.DENY, call_id=call_id, tool_name=tool_name,
                reasons=reasons, anomalies=[], risk_level="high",
            )

        # 2. Blocked actions
        if self._policy.is_action_blocked(tool_name):
            reasons.append(f"Action '{tool_name}' is blocked by policy")
            verdict = CallVerdict.DENY
            risk_level = "high"

        # 3. Human approval
        if verdict == CallVerdict.ALLOW and self._policy.needs_approval(tool_name):
            reasons.append(f"Action '{tool_name}' requires human approval")
            verdict = CallVerdict.NEED_APPROVAL
            risk_level = "medium"

        # 4. Parameter scanning
        if verdict == CallVerdict.ALLOW:
            param_issues = self._scan_params(tool_name, params)
            if param_issues:
                reasons.extend(param_issues)
                verdict = CallVerdict.DENY
                risk_level = "high"

        # 5. Network domain check
        if verdict == CallVerdict.ALLOW:
            domain_issues = self._check_domains(params)
            if domain_issues:
                reasons.extend(domain_issues)
                verdict = CallVerdict.DENY
                risk_level = "high"

        # 6. File path check
        if verdict == CallVerdict.ALLOW:
            file_issues = self._check_file_paths(tool_name, params)
            if file_issues:
                reasons.extend(file_issues)
                verdict = CallVerdict.DENY
                risk_level = "high"

        # 7. Add to DAG and check for anomalies
        dag_node = DAGNode(
            call_id=call_id,
            tool_name=tool_name,
            params_summary=_sanitize_params(params),
            timestamp=time.time(),
            risk_level=risk_level,
        )
        new_anomalies = self._dag.add_call(dag_node)
        anomalies.extend(new_anomalies)

        # Critical anomalies override verdict
        for a in new_anomalies:
            if a.severity in ("high", "critical"):
                if verdict == CallVerdict.ALLOW:
                    verdict = CallVerdict.DENY
                    reasons.append(f"Anomaly detected: {a.message}")
                    risk_level = "high"

        self._log_audit(call_id, tool_name, params, verdict, reasons)

        return InterceptResult(
            verdict=verdict, call_id=call_id, tool_name=tool_name,
            reasons=reasons, anomalies=anomalies, risk_level=risk_level,
        )

    def after_call(
        self,
        call_id: str,
        success: bool = True,
        error_message: str = "",
    ) -> None:
        """Report the result of a tool call after execution."""
        node = self._dag.nodes.get(call_id)
        if node:
            node.success = success
            tool_name = node.tool_name
        else:
            tool_name = "unknown"

        if success:
            self._breaker.record_success(tool_name)
        else:
            self._breaker.record_failure(tool_name)

        # Update audit log
        for entry in reversed(self._audit_log):
            if entry.get("call_id") == call_id:
                entry["success"] = success
                entry["error"] = error_message
                break

    def _scan_params(self, tool_name: str, params: Dict[str, Any]) -> List[str]:
        """Scan parameters for dangerous patterns."""
        issues = []
        if not self._policy.enable_dangerous_pattern_scan:
            return issues

        all_strings = _deep_string_scan(params)
        for s in all_strings:
            for pattern in _DANGEROUS_PATTERNS:
                if pattern.search(s):
                    issues.append(f"Dangerous pattern detected: {pattern.pattern}")
                    break
        return issues

    def _check_domains(self, params: Dict[str, Any]) -> List[str]:
        """Check URLs in params against network policy."""
        issues = []
        all_strings = _deep_string_scan(params)
        for s in all_strings:
            if "://" in s:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(s)
                    domain = parsed.hostname
                    if domain and not self._policy.is_domain_allowed(domain):
                        issues.append(f"Domain '{domain}' not allowed by network policy")
                except Exception:
                    pass
        return issues

    def _check_file_paths(self, tool_name: str, params: Dict[str, Any]) -> List[str]:
        """Check file paths against sensitive file patterns."""
        issues = []
        all_strings = _deep_string_scan(params)
        for s in all_strings:
            for pattern in _SENSITIVE_FILE_PATTERNS:
                if pattern in s:
                    issues.append(f"Sensitive file path detected: {s}")
                    break
        return issues

    def _log_audit(
        self, call_id: str, tool_name: str, params: Dict[str, Any],
        verdict: CallVerdict, reasons: List[str],
    ) -> None:
        """Record to audit log."""
        if self._policy.enable_audit_log:
            self._audit_log.append({
                "call_id": call_id,
                "tool_name": tool_name,
                "params_keys": list(params.keys()),
                "verdict": verdict.value,
                "reasons": reasons,
                "timestamp": time.time(),
            })
