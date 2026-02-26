"""
JadeGate Policy Layer — Security policy definition, loading, and merging.

Policies define what tool calls are allowed, blocked, or need human approval.
All enforcement is local. No data leaves the machine.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("jadegate.policy")

_DEFAULT_POLICY_PATH = os.path.join(os.path.dirname(__file__), "default_policy.json")


@dataclass
class JadePolicy:
    """
    Security policy for JadeGate runtime.

    Controls what tool calls are permitted, rate limits,
    and which operations require human approval.
    """

    # Network controls
    network_whitelist: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=lambda: [
        "169.254.169.254",
        "metadata.google.internal",
    ])

    # File system controls
    file_read_paths: List[str] = field(default_factory=list)
    file_write_paths: List[str] = field(default_factory=list)
    blocked_file_patterns: List[str] = field(default_factory=lambda: [
        "/etc/shadow", "/etc/passwd", "~/.ssh/id_",
        "~/.gnupg/", "~/.aws/credentials", "~/.config/gcloud",
    ])

    # Action controls
    blocked_actions: List[str] = field(default_factory=lambda: [
        "shell_exec", "process_spawn", "kernel_module",
    ])
    require_human_approval: List[str] = field(default_factory=lambda: [
        "email_send", "git_push", "file_delete",
    ])

    # Rate limiting
    max_calls_per_minute: int = 60
    max_call_depth: int = 20

    # Circuit breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_sec: float = 60.0

    # Scanning toggles
    enable_dangerous_pattern_scan: bool = True
    enable_executable_code_scan: bool = True

    # Audit
    enable_audit_log: bool = True
    audit_log_path: str = ""

    # File upload whitelist (only these extensions allowed)
    upload_whitelist: List[str] = field(default_factory=lambda: [
        ".json", ".txt", ".md", ".csv", ".yaml", ".yml",
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf",
    ])

    # Custom rules
    custom_rules: Dict[str, Any] = field(default_factory=dict)

    # ─── Factory methods ─────────────────────────────────────

    @classmethod
    def default(cls) -> JadePolicy:
        """Create a policy with sensible defaults."""
        if os.path.exists(_DEFAULT_POLICY_PATH):
            return cls.from_file(_DEFAULT_POLICY_PATH)
        return cls()

    @classmethod
    def permissive(cls) -> JadePolicy:
        """Permissive policy (still blocks truly dangerous stuff)."""
        return cls(
            network_whitelist=["*"],
            file_read_paths=["*"],
            file_write_paths=["*"],
            blocked_actions=["kernel_module"],
            require_human_approval=[],
            max_calls_per_minute=300,
            max_call_depth=50,
        )

    @classmethod
    def strict(cls) -> JadePolicy:
        """Strict lockdown policy."""
        return cls(
            network_whitelist=[],
            file_read_paths=[],
            file_write_paths=[],
            blocked_actions=[
                "shell_exec", "process_spawn", "kernel_module",
                "file_delete", "file_write", "http_post",
            ],
            require_human_approval=[
                "http_get", "file_read", "email_send", "git_push",
            ],
            max_calls_per_minute=20,
            max_call_depth=10,
            circuit_breaker_threshold=3,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JadePolicy:
        """Load policy from a dictionary."""
        known_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    @classmethod
    def from_file(cls, path: str) -> JadePolicy:
        """Load policy from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "jadegate_policy" in data:
            data = data["jadegate_policy"]
        return cls.from_dict(data)

    # ─── Checks ──────────────────────────────────────────────

    def is_action_blocked(self, action: str) -> bool:
        """Check if an action is blocked."""
        return action in self.blocked_actions

    def needs_approval(self, action: str) -> bool:
        """Check if an action requires human approval."""
        return action in self.require_human_approval

    def is_domain_allowed(self, domain: str) -> bool:
        """Check if a domain is allowed by network policy."""
        for blocked in self.blocked_domains:
            if domain == blocked or domain.endswith("." + blocked):
                return False
        if not self.network_whitelist:
            return True  # empty whitelist = allow all (except blocked)
        for allowed in self.network_whitelist:
            if allowed == "*":
                return True
            if domain == allowed:
                return True
            if allowed.startswith("*.") and domain.endswith(allowed[1:]):
                return True
        return False

    def is_file_path_allowed(self, path: str, mode: str = "read") -> bool:
        """Check if a file path is allowed."""
        import fnmatch
        expanded = os.path.expanduser(path)
        for pattern in self.blocked_file_patterns:
            pat_expanded = os.path.expanduser(pattern)
            if fnmatch.fnmatch(expanded, pat_expanded) or pat_expanded in expanded:
                return False
        allowed_paths = self.file_read_paths if mode == "read" else self.file_write_paths
        if not allowed_paths:
            return True  # empty = allow all (except blocked)
        for allowed in allowed_paths:
            if allowed == "*":
                return True
            if fnmatch.fnmatch(expanded, os.path.expanduser(allowed)):
                return True
        return False

    def is_upload_allowed(self, filename: str) -> bool:
        """Check if a file upload is allowed by extension whitelist."""
        if not self.upload_whitelist:
            return True
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.upload_whitelist

    # ─── Merge / Serialize ───────────────────────────────────

    def merge(self, override: JadePolicy) -> JadePolicy:
        """Merge another policy on top. Lists are unioned, scalars use override."""
        default = JadePolicy()
        merged = JadePolicy()
        for f in self.__dataclass_fields__:
            base_val = getattr(self, f)
            over_val = getattr(override, f)
            default_val = getattr(default, f)
            if isinstance(base_val, list):
                combined = list(dict.fromkeys(base_val + over_val))
                setattr(merged, f, combined)
            elif over_val != default_val:
                setattr(merged, f, over_val)
            else:
                setattr(merged, f, base_val)
        return merged

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {f: getattr(self, f) for f in self.__dataclass_fields__}

    def save(self, path: str) -> None:
        """Save policy to JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"jadegate_policy": self.to_dict()}, f, indent=2)
        logger.info("Policy saved to %s", path)
