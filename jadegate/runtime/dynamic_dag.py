"""
JadeGate Dynamic DAG — Runtime call-chain tracking and anomaly detection.

Builds a directed graph of tool calls as they happen in real time.
Detects suspicious patterns like: read sensitive file → HTTP request,
circular calls, privilege escalation, etc.

All computation is local. Nothing leaves the machine.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("jadegate.runtime.dag")


class AnomalyType(str, Enum):
    """Types of anomalies detected in call chains."""
    DATA_EXFILTRATION = "data_exfiltration"
    CIRCULAR_CALL = "circular_call"
    DEPTH_EXCEEDED = "depth_exceeded"
    RAPID_FIRE = "rapid_fire"
    PRIVILEGE_ESCALATION = "privilege_escalation"


@dataclass
class DAGNode:
    """A single tool call in the runtime DAG."""
    call_id: str
    tool_name: str
    params_summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    success: Optional[bool] = None
    duration_ms: Optional[float] = None
    risk_level: str = "unknown"
    parent_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "params_summary": self.params_summary,
            "timestamp": self.timestamp,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "risk_level": self.risk_level,
        }


@dataclass
class DAGEdge:
    """A directed edge between two calls."""
    from_id: str
    to_id: str
    edge_type: str = "sequential"

    def to_dict(self) -> Dict[str, Any]:
        return {"from": self.from_id, "to": self.to_id, "type": self.edge_type}


@dataclass
class Anomaly:
    """A detected anomaly in the call chain."""
    anomaly_type: AnomalyType
    severity: str  # low, medium, high, critical
    message: str
    involved_calls: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.anomaly_type.value,
            "severity": self.severity,
            "message": self.message,
            "involved_calls": self.involved_calls,
            "timestamp": self.timestamp,
        }


# Tool categories for pattern detection
SENSITIVE_READ_TOOLS = {
    "file_read", "read_file", "readFile", "cat", "read",
    "database_query", "db_query", "sql_query",
}
NETWORK_SEND_TOOLS = {
    "http_post", "http_put", "fetch", "curl", "request",
    "email_send", "send_email", "webhook",
    "http_request", "api_call",
}
HIGH_RISK_TOOLS = {
    "shell_exec", "execute", "run_command", "exec",
    "file_delete", "rm", "process_spawn",
}


class DynamicDAG:
    """
    Runtime call-chain DAG.

    Tracks every tool call as a node, builds edges between sequential calls,
    and runs anomaly detection patterns on the growing graph.
    """

    def __init__(self, max_depth: int = 20):
        self._nodes: Dict[str, DAGNode] = {}
        self._edges: List[DAGEdge] = []
        self._anomalies: List[Anomaly] = []
        self._call_order: List[str] = []
        self._tool_history: List[str] = []
        self._max_depth = max_depth
        self._recent_reads: List[Tuple[str, str]] = []

    @property
    def nodes(self) -> Dict[str, DAGNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> List[DAGEdge]:
        return list(self._edges)

    @property
    def anomalies(self) -> List[Anomaly]:
        return list(self._anomalies)

    @property
    def depth(self) -> int:
        return len(self._call_order)

    def add_call(self, node: DAGNode) -> List[Anomaly]:
        """Add a tool call to the DAG. Returns any new anomalies detected."""
        new_anomalies: List[Anomaly] = []

        self._nodes[node.call_id] = node
        self._call_order.append(node.call_id)
        self._tool_history.append(node.tool_name)

        # Add edge from previous call
        if len(self._call_order) > 1:
            prev_id = self._call_order[-2]
            self._edges.append(DAGEdge(from_id=prev_id, to_id=node.call_id))

        # --- Anomaly Detection ---

        # 1. Depth check
        if len(self._call_order) > self._max_depth:
            new_anomalies.append(Anomaly(
                anomaly_type=AnomalyType.DEPTH_EXCEEDED,
                severity="high",
                message=f"Call chain depth {len(self._call_order)} exceeds limit {self._max_depth}",
                involved_calls=[node.call_id],
            ))

        # 2. Data exfiltration: read sensitive → network send
        tool_lower = node.tool_name.lower()
        if tool_lower in SENSITIVE_READ_TOOLS or "read" in tool_lower or "file_read" in tool_lower:
            self._recent_reads.append((node.call_id, node.tool_name))

        if tool_lower in NETWORK_SEND_TOOLS or "http_post" in tool_lower or "send" in tool_lower:
            if self._recent_reads:
                read_ids = [r[0] for r in self._recent_reads[-3:]]
                new_anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.DATA_EXFILTRATION,
                    severity="critical",
                    message=f"Potential data exfiltration: read → {node.tool_name}",
                    involved_calls=read_ids + [node.call_id],
                ))

        # 3. Circular call detection
        if len(self._tool_history) >= 3:
            recent = self._tool_history[-3:]
            if recent[0] == recent[2] and recent[0] != recent[1]:
                new_anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.CIRCULAR_CALL,
                    severity="medium",
                    message=f"Circular call pattern: {recent[0]} → {recent[1]} → {recent[2]}",
                    involved_calls=self._call_order[-3:],
                ))

        # 4. Privilege escalation
        if tool_lower in HIGH_RISK_TOOLS and len(self._tool_history) >= 2:
            prev = self._tool_history[-2].lower()
            if prev not in HIGH_RISK_TOOLS:
                new_anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.PRIVILEGE_ESCALATION,
                    severity="high",
                    message=f"Privilege escalation: {prev} → {node.tool_name}",
                    involved_calls=self._call_order[-2:],
                ))

        self._anomalies.extend(new_anomalies)
        return new_anomalies

    def update_call(self, call_id: str, success: bool, duration_ms: float = 0) -> None:
        """Update a call node with execution results."""
        node = self._nodes.get(call_id)
        if node:
            node.success = success
            node.duration_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the DAG."""
        return {
            "nodes": {k: v.to_dict() for k, v in self._nodes.items()},
            "edges": [e.to_dict() for e in self._edges],
            "anomalies": [a.to_dict() for a in self._anomalies],
            "depth": self.depth,
        }

    def reset(self) -> None:
        """Clear the DAG."""
        self._nodes.clear()
        self._edges.clear()
        self._anomalies.clear()
        self._call_order.clear()
        self._tool_history.clear()
        self._recent_reads.clear()
