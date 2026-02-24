"""
Project JADE - Validator
The "Supreme Court" of the JADE protocol.

Validates JADE skill files against:
1. JSON Schema compliance (structural correctness)
2. Security policy enforcement (zero-trust)
3. DAG structural integrity (acyclicity, reachability)
4. Semantic consistency (cross-field validation)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    JadeSkill,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    SandboxLevel,
)
from .security import SecurityEngine
from .dag import DAGAnalyzer


class JadeValidator:
    """
    JADE Skill Validator - The gatekeeper.

    Usage:
        validator = JadeValidator()
        result = validator.validate_file("path/to/skill.json")
        if result.valid:
            print("Skill is JADE-compliant!")
        else:
            for issue in result.errors:
                print(f"[{issue.code}] {issue.message}")
    """

    SUPPORTED_VERSIONS = {"1.0.0"}
    SKILL_ID_PATTERN = re.compile(r'^[a-z][a-z0-9_]{2,63}$')
    VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')
    JADE_VERSION_PATTERN = re.compile(r'^1\.\d+\.\d+$')

    def __init__(
        self,
        schema_path: Optional[str] = None,
        allowed_actions_path: Optional[str] = None,
    ):
        self._schema: Optional[Dict[str, Any]] = None
        self._allowed_actions: List[str] = []
        self._security_engine = SecurityEngine()
        self._dag_analyzer = DAGAnalyzer()

        # Load schema if provided
        if schema_path:
            self.load_schema(schema_path)
        else:
            self._load_default_schema()

        # Load allowed actions if provided
        if allowed_actions_path:
            self.load_allowed_actions(allowed_actions_path)
        else:
            self._load_default_allowed_actions()

    def _load_default_schema(self) -> None:
        """Load the default schema from jade_schema directory."""
        schema_dir = Path(__file__).parent.parent / "jade_schema"
        schema_file = schema_dir / "jade-schema-v1.json"
        if schema_file.exists():
            with open(schema_file, "r", encoding="utf-8") as f:
                self._schema = json.load(f)

    def _load_default_allowed_actions(self) -> None:
        """Load the default allowed actions from jade_schema directory."""
        schema_dir = Path(__file__).parent.parent / "jade_schema"
        actions_file = schema_dir / "allowed_atomic_actions.json"
        if actions_file.exists():
            with open(actions_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._allowed_actions = self._extract_action_names(data)
                self._security_engine.set_allowed_actions(self._allowed_actions)

    def _extract_action_names(self, data: Dict[str, Any]) -> List[str]:
        """Extract all action names from the allowed_atomic_actions.json structure."""
        actions = []
        categories = data.get("categories", {})
        for cat_name, cat_data in categories.items():
            cat_actions = cat_data.get("actions", {})
            actions.extend(cat_actions.keys())
        return actions

    def load_schema(self, path: str) -> None:
        """Load a JADE schema from file."""
        with open(path, "r", encoding="utf-8") as f:
            self._schema = json.load(f)

    def load_allowed_actions(self, path: str) -> None:
        """Load allowed atomic actions from file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._allowed_actions = self._extract_action_names(data)
            self._security_engine.set_allowed_actions(self._allowed_actions)

    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate a JADE skill JSON file."""
        issues: List[ValidationIssue] = []

        # 0. Path sanitization — prevent path traversal
        file_path = os.path.realpath(file_path)
        if ".." in os.path.relpath(file_path):
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="PATH_TRAVERSAL",
                    message="Path traversal detected. Use absolute paths or paths without '..'",
                    hint="Provide a direct path to the skill JSON file.",
                )],
            )

        # 1. File existence and readability
        if not os.path.exists(file_path):
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="FILE_NOT_FOUND",
                    message=f"File not found: {file_path}",
                )],
            )

        # 2. JSON parsing
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_JSON",
                    message=f"Invalid JSON: {e}",
                )],
            )

        return self.validate_dict(raw_data, source_path=file_path)

    def validate_dict(self, data: Dict[str, Any], source_path: str = "<memory>") -> ValidationResult:
        """Validate a JADE skill from a dictionary."""
        issues: List[ValidationIssue] = []

        # 3. Structural validation (required fields)
        issues.extend(self._check_required_fields(data))
        if any(i.severity == ValidationSeverity.ERROR for i in issues):
            return ValidationResult(valid=False, issues=issues)

        # 4. Parse into model
        try:
            skill = JadeSkill.from_dict(data)
        except Exception as e:
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="PARSE_ERROR",
                    message=f"Failed to parse skill: {e}",
                    hint="Check that all required fields exist and have correct types. Run: jade verify examples/hello_world.json to see a working example.",
                )],
            )

        # 5. Version check
        issues.extend(self._check_version(skill))

        # 6. Metadata validation
        issues.extend(self._check_metadata(skill))

        # 7. Trigger validation
        issues.extend(self._check_trigger(skill))

        # 8. DAG validation
        issues.extend(self._dag_analyzer.validate(skill))

        # 9. Security validation
        issues.extend(self._security_engine.check_all(skill))

        # 10. Semantic cross-validation
        issues.extend(self._check_semantic_consistency(skill))

        # Compute skill hash
        skill_hash = self._compute_skill_hash(data)

        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)
        return ValidationResult(
            valid=not has_errors,
            issues=issues,
            skill_hash=skill_hash,
            checked_at=time.time(),
        )

    def _check_required_fields(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Check that all required top-level fields are present."""
        issues: List[ValidationIssue] = []
        required = ["jade_version", "skill_id", "metadata", "trigger", "execution_dag", "security"]
        for field_name in required:
            if field_name not in data:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_FIELD",
                    message=f"Required field '{field_name}' is missing",
                    path=field_name,
                    hint=f"Add '{field_name}' to your skill JSON. See examples/ for reference.",
                ))
        return issues

    def _check_version(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Validate JADE protocol version."""
        issues: List[ValidationIssue] = []
        if not self.JADE_VERSION_PATTERN.match(skill.jade_version):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="UNSUPPORTED_VERSION",
                message=f"jade_version '{skill.jade_version}' must match pattern '1.x.x'. "
                        f"Supported versions: {self.SUPPORTED_VERSIONS}",
                path="jade_version",
                hint="Use \"jade_version\": \"1.0.0\"",
            ))
        elif skill.jade_version not in self.SUPPORTED_VERSIONS:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="UNSUPPORTED_VERSION",
                message=f"jade_version '{skill.jade_version}' is not in supported versions: {self.SUPPORTED_VERSIONS}",
                path="jade_version",
            ))
        return issues

    def _check_metadata(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Validate metadata fields."""
        issues: List[ValidationIssue] = []
        meta = skill.metadata

        if not self.SKILL_ID_PATTERN.match(skill.skill_id):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_SKILL_ID",
                message=f"skill_id '{skill.skill_id}' must match pattern '^[a-z][a-z0-9_]{{2,63}}$'",
                path="skill_id",
                hint="Use lowercase letters, numbers, and underscores only. Example: \"my_cool_tool\"",
            ))

        if not meta.name or len(meta.name) > 128:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_METADATA_NAME",
                message="metadata.name must be 1-128 characters",
                path="metadata.name",
            ))

        if not self.VERSION_PATTERN.match(meta.version):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_METADATA_VERSION",
                message=f"metadata.version '{meta.version}' must match 'x.y.z'",
                path="metadata.version",
            ))

        if not meta.description or len(meta.description) > 1024:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_METADATA_DESC",
                message="metadata.description must be 1-1024 characters",
                path="metadata.description",
            ))

        if not meta.tags or len(meta.tags) > 10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_METADATA_TAGS",
                message="metadata.tags must have 1-10 items",
                path="metadata.tags",
            ))

        if len(meta.tags) != len(set(meta.tags)):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="DUPLICATE_TAGS",
                message="metadata.tags contains duplicate entries",
                path="metadata.tags",
            ))

        return issues

    def _check_trigger(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Validate trigger configuration."""
        issues: List[ValidationIssue] = []
        trigger = skill.trigger

        if not trigger.conditions:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="NO_TRIGGER_CONDITIONS",
                message="Trigger must have at least one condition",
                path="trigger.conditions",
            ))

        return issues

    def _check_semantic_consistency(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Cross-field semantic validation."""
        issues: List[ValidationIssue] = []
        dag = skill.execution_dag
        security = skill.security

        # Check: if network_whitelist is empty, no node should use network actions
        network_actions = {"http_get", "http_post", "dns_resolve", "smtp_send"}
        if not security.network_whitelist:
            for node in dag.nodes:
                if node.action in network_actions:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="NETWORK_ACTION_NO_WHITELIST",
                        message=f"Node '{node.id}' uses network action '{node.action}' "
                                f"but network_whitelist is empty",
                        path=f"execution_dag.nodes.{node.id}",
                    ))

        # Check: if file_permissions are empty, no node should use file actions
        file_actions = {"file_read", "file_write", "file_list", "file_delete", "file_copy", "file_move"}
        if not security.file_read_paths and not security.file_write_paths:
            for node in dag.nodes:
                if node.action in file_actions:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="FILE_ACTION_NO_PERMS",
                        message=f"Node '{node.id}' uses file action '{node.action}' "
                                f"but no file permissions are declared",
                        path=f"execution_dag.nodes.{node.id}",
                    ))

        # Check: max_retries consistency
        if security.max_retries == 0:
            retry_config = skill.raw_data.get("execution_dag", {}).get("max_retries")
            if retry_config and retry_config.get("max_count", 0) > 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="RETRY_MISMATCH",
                    message="execution_dag defines retries but security.max_retries is 0",
                    path="security.max_retries",
                ))

        return issues

    def _compute_skill_hash(self, data: Dict[str, Any]) -> str:
        """Compute a deterministic SHA-256 hash of the skill content."""
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def validate_batch(self, file_paths: List[str]) -> Dict[str, ValidationResult]:
        """Validate multiple skill files."""
        results: Dict[str, ValidationResult] = {}
        for path in file_paths:
            results[path] = self.validate_file(path)
        return results
