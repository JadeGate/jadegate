"""
Project JADE - Data Models
Deterministic Security Protocol for AI Agents

All data structures used across the JADE ecosystem.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TriggerType(str, Enum):
    ERROR_CODE = "error_code"
    TASK_INTENT = "task_intent"
    ENVIRONMENT_STATE = "environment_state"
    MANUAL = "manual"
    MCP_CALL = "mcp_call"
    DIRECT_CALL = "direct_call"
    HTTP_REQUEST = "http_request"
    SCHEDULED = "scheduled"
    EVENT = "event"


class ConditionOperator(str, Enum):
    EQUALS = "equals"
    CONTAINS = "contains"
    MATCHES = "matches"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_CONTAINS = "not_contains"


class SandboxLevel(str, Enum):
    STRICT = "strict"
    STANDARD = "standard"
    PERMISSIVE = "permissive"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttestationType(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue found during skill verification."""
    severity: ValidationSeverity
    code: str
    message: str
    path: str = ""  # JSON path to the problematic field

    def to_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class ValidationResult:
    """Result of validating a JADE skill."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    skill_hash: str = ""
    checked_at: float = field(default_factory=time.time)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "skill_hash": self.skill_hash,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "checked_at": self.checked_at,
        }


@dataclass
class TriggerCondition:
    """A single trigger condition."""
    field: str
    operator: ConditionOperator
    value: Any

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TriggerCondition:
        return cls(
            field=data["field"],
            operator=ConditionOperator(data["operator"]),
            value=data["value"],
        )


@dataclass
class Trigger:
    """Skill trigger definition."""
    type: TriggerType
    conditions: List[TriggerCondition]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Trigger:
        return cls(
            type=TriggerType(data["type"]),
            conditions=[TriggerCondition.from_dict(c) for c in data["conditions"]],
        )


@dataclass
class DAGNode:
    """A node in the execution DAG."""
    id: str
    action: str
    params: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DAGNode:
        return cls(id=data["id"], action=data["action"], params=data["params"])


@dataclass
class DAGEdge:
    """An edge in the execution DAG."""
    from_node: str
    to_node: str
    condition: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DAGEdge:
        return cls(
            from_node=data["from"],
            to_node=data["to"],
            condition=data.get("condition"),
        )


@dataclass
class ExecutionDAG:
    """The execution Directed Acyclic Graph."""
    nodes: List[DAGNode]
    edges: List[DAGEdge]
    entry_node: str
    exit_node: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionDAG:
        exit_node = data["exit_node"]
        if isinstance(exit_node, str):
            exit_node = [exit_node]
        return cls(
            nodes=[DAGNode.from_dict(n) for n in data["nodes"]],
            edges=[DAGEdge.from_dict(e) for e in data["edges"]],
            entry_node=data["entry_node"],
            exit_node=exit_node,
        )

    def get_node(self, node_id: str) -> Optional[DAGNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_outgoing_edges(self, node_id: str) -> List[DAGEdge]:
        return [e for e in self.edges if e.from_node == node_id]

    def get_incoming_edges(self, node_id: str) -> List[DAGEdge]:
        return [e for e in self.edges if e.to_node == node_id]


@dataclass
class SecurityPolicy:
    """Security constraints for a skill."""
    network_whitelist: List[str]
    file_read_paths: List[str]
    file_write_paths: List[str]
    max_execution_time_ms: int
    max_retries: int
    sandbox_level: SandboxLevel
    dangerous_patterns: List[str]
    env_whitelist: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SecurityPolicy:
        file_perms = data.get("file_permissions", {})
        return cls(
            network_whitelist=data.get("network_whitelist", []),
            file_read_paths=file_perms.get("read", []),
            file_write_paths=file_perms.get("write", []),
            max_execution_time_ms=data.get("max_execution_time_ms", 30000),
            max_retries=data.get("max_retries", 3),
            sandbox_level=SandboxLevel(data.get("sandbox_level", "strict")),
            dangerous_patterns=data.get("dangerous_patterns", []),
            env_whitelist=data.get("env_whitelist", []),
        )


@dataclass
class SkillMetadata:
    """Metadata for a JADE skill."""
    name: str
    version: str
    description: str
    author: str
    tags: List[str]
    license: str = "MIT"
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SkillMetadata:
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            tags=data["tags"],
            license=data.get("license", "MIT"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class JadeSkill:
    """A complete JADE skill definition."""
    jade_version: str
    skill_id: str
    metadata: SkillMetadata
    trigger: Trigger
    execution_dag: ExecutionDAG
    security: SecurityPolicy
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    mcp_compatible: bool = False
    required_mcp_capabilities: List[str] = field(default_factory=list)

    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JadeSkill:
        return cls(
            jade_version=data["jade_version"],
            skill_id=data["skill_id"],
            metadata=SkillMetadata.from_dict(data["metadata"]),
            trigger=Trigger.from_dict(data["trigger"]),
            execution_dag=ExecutionDAG.from_dict(data["execution_dag"]),
            security=SecurityPolicy.from_dict(data["security"]),
            input_schema=data.get("input_schema"),
            output_schema=data.get("output_schema"),
            mcp_compatible=data.get("mcp_compatible", False),
            required_mcp_capabilities=data.get("required_mcp_capabilities", []),
            raw_data=data,
        )

    @classmethod
    def from_json(cls, json_str: str) -> JadeSkill:
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_file(cls, path: str) -> JadeSkill:
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def compute_hash(self) -> str:
        """Compute a deterministic SHA-256 hash of this skill."""
        canonical = json.dumps(
            {
                "jade_version": self.jade_version,
                "skill_id": self.skill_id,
                "metadata": {"name": self.metadata.name, "version": self.metadata.version},
                "execution_dag": {
                    "nodes": [{"id": n.id, "action": n.action, "params": n.params} for n in self.execution_dag.nodes],
                    "edges": [{"from": e.from_node, "to": e.to_node, "condition": e.condition} for e in self.execution_dag.edges],
                },
                "security": {
                    "network_whitelist": self.security.network_whitelist,
                    "sandbox_level": self.security.sandbox_level.value,
                },
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class RegistryEntry:
    """An entry in the JADE skill registry index."""
    skill_id: str
    skill_hash: str
    confidence_score: float
    success_count: int = 0
    failure_count: int = 0
    last_verified: float = field(default_factory=time.time)
    source_url: str = ""
    signature: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_hash": self.skill_hash,
            "confidence_score": self.confidence_score,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_verified": self.last_verified,
            "source_url": self.source_url,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RegistryEntry:
        return cls(
            skill_id=data["skill_id"],
            skill_hash=data["skill_hash"],
            confidence_score=data["confidence_score"],
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            last_verified=data.get("last_verified", 0),
            source_url=data.get("source_url", ""),
            signature=data.get("signature", ""),
        )


@dataclass
class Attestation:
    """A success/failure attestation submitted by an agent."""
    skill_id: str
    skill_hash: str
    success: bool
    execution_time_ms: int
    attestation_type: AttestationType = AttestationType.SUCCESS
    agent_id: str = ""
    timestamp: float = field(default_factory=time.time)
    error_code: str = ""
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_hash": self.skill_hash,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "attestation_type": self.attestation_type.value,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Attestation:
        return cls(
            skill_id=data["skill_id"],
            skill_hash=data["skill_hash"],
            success=data["success"],
            execution_time_ms=data["execution_time_ms"],
            attestation_type=AttestationType(data.get("attestation_type", "success")),
            agent_id=data.get("agent_id", ""),
            timestamp=data.get("timestamp", 0),
            error_code=data.get("error_code", ""),
            error_message=data.get("error_message", ""),
        )
