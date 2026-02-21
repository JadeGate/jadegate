"""
Project JADE - Security Engine
Zero-Trust security verification for JADE skills.

This module enforces:
1. No executable code (non-Turing-complete check)
2. Network whitelist enforcement
3. Dangerous pattern detection (rm -rf, mkfs, etc.)
4. File permission boundary checks
5. Sandbox level enforcement
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

from .models import (
    JadeSkill,
    SecurityPolicy,
    SandboxLevel,
    ValidationIssue,
    ValidationSeverity,
)

# Patterns that indicate executable code injection
EXECUTABLE_CODE_PATTERNS = [
    r'\bexec\s*\(',
    r'\beval\s*\(',
    r'\bimport\s+',
    r'\b__import__\s*\(',
    r'\bos\.system\s*\(',
    r'\bsubprocess\b',
    r'\bcompile\s*\(',
    r'<script\b',
    r'javascript:',
    r'\bFunction\s*\(',
    r'\bsetTimeout\s*\(',
    r'\bsetInterval\s*\(',
    r'\bchild_process\b',
    r'\brequire\s*\(\s*["\']child_process',
    r'\bsystem\s*\(',
    r'\bpopen\s*\(',
    r'\bShellExecute\b',
    r'\bWScript\b',
    r'\bpowershell\b',
    r'\bcmd\.exe\b',
    r'\b/bin/sh\b',
    r'\b/bin/bash\b',
]

# Dangerous system commands
DANGEROUS_COMMANDS = [
    r'\brm\s+-rf\b',
    r'\brm\s+-fr\b',
    r'\bmkfs\b',
    r'\bdd\s+if=',
    r'\bformat\s+[cCdD]:',
    r'\bfdisk\b',
    r'\bchmod\s+777\b',
    r'\bchmod\s+-R\s+777\b',
    r'\b:(){ :\|:& };:',  # fork bomb
    r'\bshutdown\b',
    r'\breboot\b',
    r'\binit\s+0\b',
    r'\bhalt\b',
    r'\bkillall\b',
    r'\biptables\s+-F\b',
    r'\bsudo\s+',
    r'\bsu\s+-\b',
    r'\bcrontab\b',
    r'\bwget\s+.*\|\s*sh\b',
    r'\bcurl\s+.*\|\s*sh\b',
    r'\bcurl\s+.*\|\s*bash\b',
    r'\bnc\s+-[el]',  # netcat listener
    r'\bncat\b',
    r'\btelnet\b',
    r'\bssh\s+.*@',
    r'\bscp\s+',
    r'\brsync\s+.*@',
]

# Suspicious network patterns
SUSPICIOUS_NETWORK_PATTERNS = [
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # Raw IP addresses
    r'localhost',
    r'127\.0\.0\.1',
    r'0\.0\.0\.0',
    r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # Private IP ranges
    r'172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}',
    r'192\.168\.\d{1,3}\.\d{1,3}',
    r'\.onion$',
    r'\.i2p$',
]

# Data exfiltration patterns
DATA_EXFIL_PATTERNS = [
    r'api[_-]?key',
    r'secret[_-]?key',
    r'private[_-]?key',
    r'access[_-]?token',
    r'password',
    r'passwd',
    r'credential',
    r'\.env\b',
    r'\.ssh/',
    r'id_rsa',
    r'\.aws/credentials',
    r'\.kube/config',
]


class SecurityEngine:
    """
    JADE Security Engine - The "immune system" of the protocol.

    Performs deep inspection of skill definitions to ensure they are:
    1. Non-Turing-complete (no executable code)
    2. Network-safe (whitelist enforced)
    3. File-safe (permission boundaries)
    4. Free of dangerous patterns
    """

    def __init__(self, allowed_actions: List[str] | None = None):
        self._allowed_actions: Set[str] = set(allowed_actions) if allowed_actions else set()
        self._compiled_exec_patterns = [re.compile(p, re.IGNORECASE) for p in EXECUTABLE_CODE_PATTERNS]
        self._compiled_danger_patterns = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_COMMANDS]
        self._compiled_network_patterns = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_NETWORK_PATTERNS]
        self._compiled_exfil_patterns = [re.compile(p, re.IGNORECASE) for p in DATA_EXFIL_PATTERNS]

    def set_allowed_actions(self, actions: List[str]) -> None:
        self._allowed_actions = set(actions)

    def check_all(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Run all security checks on a skill."""
        issues: List[ValidationIssue] = []
        issues.extend(self.check_no_executable_code(skill))
        issues.extend(self.check_dangerous_patterns(skill))
        issues.extend(self.check_network_whitelist(skill))
        issues.extend(self.check_file_permissions(skill))
        issues.extend(self.check_allowed_actions(skill))
        issues.extend(self.check_sandbox_constraints(skill))
        issues.extend(self.check_data_exfiltration(skill))
        return issues

    def check_no_executable_code(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Ensure no executable code patterns exist in any string values."""
        issues: List[ValidationIssue] = []
        all_strings = self._extract_all_strings(skill)

        for path, value in all_strings:
            for pattern in self._compiled_exec_patterns:
                match = pattern.search(value)
                if match:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="SEC_EXEC_CODE",
                        message=f"Executable code pattern detected: '{match.group()}'. "
                                f"JADE skills must be non-Turing-complete.",
                        path=path,
                    ))
        return issues

    def check_dangerous_patterns(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Check for dangerous system commands."""
        issues: List[ValidationIssue] = []
        all_strings = self._extract_all_strings(skill)

        for path, value in all_strings:
            for pattern in self._compiled_danger_patterns:
                match = pattern.search(value)
                if match:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="SEC_DANGEROUS_CMD",
                        message=f"Dangerous system command detected: '{match.group()}'",
                        path=path,
                    ))
        return issues

    def check_network_whitelist(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Verify network access is properly whitelisted."""
        issues: List[ValidationIssue] = []
        policy = skill.security
        whitelist = set(policy.network_whitelist)

        # If strict sandbox, network_whitelist must not be wildcard
        if policy.sandbox_level == SandboxLevel.STRICT and "*" in whitelist:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="SEC_WILDCARD_NETWORK",
                message="Wildcard '*' in network_whitelist with strict sandbox. "
                        "Consider specifying exact domains.",
                path="security.network_whitelist",
            ))

        # Check for suspicious domains in whitelist
        for domain in whitelist:
            if domain == "*":
                continue
            for pattern in self._compiled_network_patterns:
                if pattern.search(domain):
                    # In strict sandbox, suspicious networks are errors
                    severity = (
                        ValidationSeverity.ERROR
                        if policy.sandbox_level == SandboxLevel.STRICT
                        else ValidationSeverity.WARNING
                    )
                    issues.append(ValidationIssue(
                        severity=severity,
                        code="SEC_SUSPICIOUS_NETWORK",
                        message=f"Suspicious domain in whitelist: '{domain}'. "
                                f"Private IPs and special TLDs are flagged.",
                        path="security.network_whitelist",
                    ))

        # Check that all URLs in DAG nodes match the whitelist
        if "*" not in whitelist:
            for node in skill.execution_dag.nodes:
                urls = self._extract_urls_from_params(node.params)
                for url in urls:
                    domain = self._extract_domain(url)
                    if domain and not self._domain_matches_whitelist(domain, whitelist):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="SEC_UNLISTED_DOMAIN",
                            message=f"Node '{node.id}' accesses domain '{domain}' "
                                    f"not in network_whitelist",
                            path=f"execution_dag.nodes.{node.id}.params",
                        ))

        return issues

    def check_file_permissions(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Verify file access is within declared permissions."""
        issues: List[ValidationIssue] = []
        policy = skill.security

        # Check for overly broad file permissions
        for path in policy.file_read_paths + policy.file_write_paths:
            if path in ("/", "/*", "C:\\", "C:\\*"):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="SEC_ROOT_FILE_ACCESS",
                    message=f"Root-level file access is forbidden: '{path}'",
                    path="security.file_permissions",
                ))

        # Check for sensitive file paths
        sensitive_paths = [
            "/etc/passwd", "/etc/shadow", "~/.ssh/", "~/.aws/",
            "~/.kube/", "/proc/", "/sys/", "/dev/",
        ]
        for perm_path in policy.file_read_paths + policy.file_write_paths:
            for sensitive in sensitive_paths:
                if sensitive in perm_path:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="SEC_SENSITIVE_PATH",
                        message=f"Access to sensitive path forbidden: '{perm_path}'",
                        path="security.file_permissions",
                    ))

        return issues

    def check_allowed_actions(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Verify all actions in DAG are from the allowed actions list."""
        issues: List[ValidationIssue] = []
        if not self._allowed_actions:
            return issues  # No action list loaded, skip check

        for node in skill.execution_dag.nodes:
            if node.action not in self._allowed_actions:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="SEC_UNKNOWN_ACTION",
                    message=f"Action '{node.action}' is not in the allowed atomic actions list. "
                            f"Node: '{node.id}'",
                    path=f"execution_dag.nodes.{node.id}.action",
                ))

        return issues

    def check_sandbox_constraints(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Enforce sandbox-level-specific constraints."""
        issues: List[ValidationIssue] = []
        policy = skill.security

        if policy.sandbox_level == SandboxLevel.STRICT:
            # Strict: max execution time <= 120s
            if policy.max_execution_time_ms > 120000:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="SEC_TIMEOUT_EXCEEDED",
                    message=f"Strict sandbox: max_execution_time_ms ({policy.max_execution_time_ms}) "
                            f"exceeds 120000ms limit",
                    path="security.max_execution_time_ms",
                ))
            # Strict: max retries <= 10
            if policy.max_retries > 10:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="SEC_RETRIES_EXCEEDED",
                    message=f"Strict sandbox: max_retries ({policy.max_retries}) exceeds 10 limit",
                    path="security.max_retries",
                ))

        return issues

    def check_data_exfiltration(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Check for potential data exfiltration patterns in all string values."""
        issues: List[ValidationIssue] = []
        all_strings = self._extract_all_strings(skill)

        for path, value in all_strings:
            for pattern in self._compiled_exfil_patterns:
                match = pattern.search(value)
                if match:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="SEC_DATA_EXFIL_RISK",
                        message=f"Potential data exfiltration: "
                                f"sensitive pattern '{match.group()}' found",
                        path=path,
                    ))

        return issues

    # ---- Internal helpers ----

    def _extract_all_strings(self, skill: JadeSkill) -> List[tuple]:
        """Recursively extract all string values from the skill with their paths."""
        results: List[tuple] = []
        for i, node in enumerate(skill.execution_dag.nodes):
            self._walk_dict(node.params, f"execution_dag.nodes[{i}].params", results)
        return results

    def _walk_dict(self, obj: Any, path: str, results: List[tuple]) -> None:
        if isinstance(obj, str):
            results.append((path, obj))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self._walk_dict(v, f"{path}.{k}", results)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                self._walk_dict(v, f"{path}[{i}]", results)

    def _extract_urls_from_params(self, params: Dict[str, Any]) -> List[str]:
        """Extract URL-like strings from params."""
        urls: List[str] = []
        self._find_urls(params, urls)
        return urls

    def _find_urls(self, obj: Any, urls: List[str]) -> None:
        if isinstance(obj, str):
            # Match template variables like {{input.target_url}} or actual URLs
            if obj.startswith("http://") or obj.startswith("https://"):
                urls.append(obj)
            elif "://" in obj:
                urls.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                self._find_urls(v, urls)
        elif isinstance(obj, list):
            for v in obj:
                self._find_urls(v, urls)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from a URL, handling template variables."""
        # Skip template variables
        if "{{" in url:
            # Try to extract static domain parts
            # e.g., "https://wttr.in/{{input.location}}" -> "wttr.in"
            try:
                clean = re.sub(r'\{\{[^}]+\}\}', 'PLACEHOLDER', url)
                parsed = urlparse(clean)
                return parsed.hostname or ""
            except Exception:
                return ""
        try:
            parsed = urlparse(url)
            return parsed.hostname or ""
        except Exception:
            return ""

    def _domain_matches_whitelist(self, domain: str, whitelist: Set[str]) -> bool:
        """Check if a domain matches any entry in the whitelist."""
        for allowed in whitelist:
            if allowed == "*":
                return True
            if domain == allowed:
                return True
            # Support wildcard subdomains: *.example.com
            if allowed.startswith("*.") and domain.endswith(allowed[1:]):
                return True
        return False
