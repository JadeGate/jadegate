"""
JadeGate Certificate — Security certificates for tools and MCP servers.

Each tool/server gets a certificate describing its capabilities, risk profile,
and trust status. Certificates are signed with Ed25519 (reusing jade_core crypto).

All stored locally in ~/.jadegate/trust/
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("jadegate.trust.certificate")


@dataclass
class RiskProfile:
    """Risk assessment for a tool."""
    level: str = "unknown"  # low, medium, high, critical, unknown
    capabilities: List[str] = field(default_factory=list)
    network_access: bool = False
    file_access: bool = False
    shell_access: bool = False
    data_exfil_risk: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "capabilities": self.capabilities,
            "network_access": self.network_access,
            "file_access": self.file_access,
            "shell_access": self.shell_access,
            "data_exfil_risk": self.data_exfil_risk,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RiskProfile:
        return cls(
            level=data.get("level", "unknown"),
            capabilities=data.get("capabilities", []),
            network_access=data.get("network_access", False),
            file_access=data.get("file_access", False),
            shell_access=data.get("shell_access", False),
            data_exfil_risk=data.get("data_exfil_risk", False),
        )

    @classmethod
    def from_tool_info(cls, name: str, description: str = "", input_schema: Optional[Dict] = None) -> RiskProfile:
        """Auto-generate risk profile from tool metadata."""
        text = f"{name} {description}".lower()
        caps: List[str] = []
        net = False
        file_acc = False
        shell = False
        exfil = False

        if any(kw in text for kw in ("http", "fetch", "request", "url", "api", "webhook", "curl")):
            net = True
            caps.append("network")
        if any(kw in text for kw in ("file", "read", "write", "path", "directory", "folder")):
            file_acc = True
            caps.append("filesystem")
        if any(kw in text for kw in ("exec", "shell", "command", "run", "bash", "terminal")):
            shell = True
            caps.append("shell")
        if any(kw in text for kw in ("send", "email", "post", "upload", "push")):
            exfil = True
            caps.append("data_send")
        if any(kw in text for kw in ("search", "query", "list", "get")):
            caps.append("read_only")

        if shell:
            level = "critical"
        elif net and file_acc:
            level = "high"
        elif net or exfil:
            level = "medium"
        elif file_acc:
            level = "medium"
        else:
            level = "low"

        return cls(
            level=level, capabilities=caps, network_access=net,
            file_access=file_acc, shell_access=shell, data_exfil_risk=exfil,
        )


@dataclass
class JadeCertificate:
    """
    Security certificate for a tool or MCP server.
    Similar to X.509 but for AI tools.
    """
    tool_id: str
    server_id: str = ""
    display_name: str = ""
    description: str = ""
    risk_profile: RiskProfile = field(default_factory=RiskProfile)
    trust_score: float = 0.5  # Bayesian prior
    success_count: int = 0
    failure_count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    signed_by: str = ""  # public key fingerprint of signer
    signature: str = ""  # Ed25519 signature
    version: str = "1.0"

    def compute_fingerprint(self) -> str:
        """Compute SHA-256 fingerprint of the certificate content."""
        content = json.dumps(self._signable_content(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _signable_content(self) -> Dict[str, Any]:
        """Content that gets signed (excludes signature itself)."""
        return {
            "tool_id": self.tool_id,
            "server_id": self.server_id,
            "display_name": self.display_name,
            "risk_profile": self.risk_profile.to_dict(),
            "version": self.version,
        }

    def update_trust(self, success: bool) -> float:
        """Bayesian update of trust score. Returns new score."""
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        alpha = self.success_count + 1  # Laplace smoothing
        beta = self.failure_count + 1
        self.trust_score = alpha / (alpha + beta)
        self.last_seen = time.time()
        return self.trust_score

    def sign(self, private_key_str: str) -> bool:
        """Sign this certificate with an Ed25519 private key."""
        try:
            from jade_core.crypto import JadeKeyPair
            content = json.dumps(self._signable_content(), sort_keys=True, separators=(",", ":"))
            kp = JadeKeyPair.from_private_key(private_key_str)
            self.signature = kp.sign(content.encode())
            self.signed_by = kp.fingerprint
            return True
        except Exception as e:
            logger.warning("Failed to sign certificate: %s", e)
            return False

    def verify(self, public_key_str: str) -> bool:
        """Verify the certificate signature."""
        if not self.signature:
            return False
        try:
            from jade_core.crypto import JadeKeyPair
            content = json.dumps(self._signable_content(), sort_keys=True, separators=(",", ":"))
            return JadeKeyPair.verify(content.encode(), self.signature, public_key_str)
        except Exception as e:
            logger.warning("Failed to verify certificate: %s", e)
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "server_id": self.server_id,
            "display_name": self.display_name,
            "description": self.description,
            "risk_profile": self.risk_profile.to_dict(),
            "trust_score": self.trust_score,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "signed_by": self.signed_by,
            "signature": self.signature,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JadeCertificate:
        rp_data = data.get("risk_profile", {})
        if isinstance(rp_data, dict):
            rp = RiskProfile.from_dict(rp_data)
        else:
            rp = RiskProfile(level=str(rp_data))
        return cls(
            tool_id=data["tool_id"],
            server_id=data.get("server_id", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            risk_profile=rp,
            trust_score=data.get("trust_score", 0.5),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            first_seen=data.get("first_seen", time.time()),
            last_seen=data.get("last_seen", time.time()),
            signed_by=data.get("signed_by", ""),
            signature=data.get("signature", ""),
            version=data.get("version", "1.0"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> JadeCertificate:
        return cls.from_dict(json.loads(json_str))
