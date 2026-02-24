"""
Project JADE - Deterministic Security Protocol for AI Agents
=============================================================

The Package Manager and Immunity Network for AI Agents.

Core modules:
- models: Data structures and types
- validator: Schema and security validation
- security: Zero-trust security engine
- dag: DAG structural analysis
- client: SDK for agents to fetch and use skills
- registry: Index management and confidence scoring
"""

__version__ = "1.3.2"
__protocol_version__ = "1.0.0"

from .models import (
    JadeSkill,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    SecurityPolicy,
    ExecutionDAG,
    DAGNode,
    DAGEdge,
    Trigger,
    TriggerCondition,
    SkillMetadata,
    SandboxLevel,
    TriggerType,
    ConditionOperator,
    RiskLevel,
    RegistryEntry,
    Attestation,
    AttestationType,
)
from .validator import JadeValidator
from .security import SecurityEngine
from .dag import DAGAnalyzer
from .client import JadeClient
from .registry import JadeRegistry

__all__ = [
    # Core classes
    "JadeValidator",
    "SecurityEngine",
    "DAGAnalyzer",
    "JadeClient",
    "JadeRegistry",
    # Models
    "JadeSkill",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "SecurityPolicy",
    "ExecutionDAG",
    "DAGNode",
    "DAGEdge",
    "Trigger",
    "TriggerCondition",
    "SkillMetadata",
    "SandboxLevel",
    "TriggerType",
    "ConditionOperator",
    "RiskLevel",
    "RegistryEntry",
    "Attestation",
    "AttestationType",
]
