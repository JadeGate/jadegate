"""
JadeGate Trust Store — Local certificate storage.

Stores tool certificates in ~/.jadegate/trust/ as JSON files.
Similar to a browser's CA certificate store, but for AI tools.

All data stays local.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from .certificate import JadeCertificate

logger = logging.getLogger("jadegate.trust.trust_store")

DEFAULT_TRUST_DIR = os.path.join(str(Path.home()), ".jadegate", "trust")


class LocalTrustStore:
    """
    Local trust store for JadeCertificates.

    Stores certificates as JSON files in ~/.jadegate/trust/
    Provides lookup, save, and trust status queries.
    """

    def __init__(self, trust_dir: Optional[str] = None):
        self._trust_dir = trust_dir or DEFAULT_TRUST_DIR
        Path(self._trust_dir).mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, JadeCertificate] = {}
        self._load_all()

    def _cert_path(self, tool_id: str) -> str:
        safe_id = tool_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self._trust_dir, f"{safe_id}.cert.json")

    def _load_all(self) -> None:
        """Load all certificates from disk."""
        trust_path = Path(self._trust_dir)
        if not trust_path.exists():
            return
        for f in trust_path.glob("*.cert.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                cert = JadeCertificate.from_dict(data)
                self._cache[cert.tool_id] = cert
            except Exception as e:
                logger.warning("Failed to load cert %s: %s", f, e)

    def get(self, tool_id: str) -> Optional[JadeCertificate]:
        """Get a certificate by tool_id."""
        return self._cache.get(tool_id)

    def save(self, cert: JadeCertificate) -> None:
        """Save a certificate to disk and cache."""
        self._cache[cert.tool_id] = cert
        path = self._cert_path(cert.tool_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cert.to_dict(), f, indent=2)
        logger.debug("Saved certificate for '%s'", cert.tool_id)

    def remove(self, tool_id: str) -> bool:
        """Remove a certificate."""
        if tool_id in self._cache:
            del self._cache[tool_id]
        path = self._cert_path(tool_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def list_all(self) -> List[JadeCertificate]:
        """List all stored certificates."""
        return list(self._cache.values())

    def is_trusted(self, tool_id: str, min_score: float = 0.6) -> bool:
        """Check if a tool is trusted (has cert with sufficient trust score)."""
        cert = self._cache.get(tool_id)
        if not cert:
            return False
        return cert.trust_score >= min_score

    def is_signed(self, tool_id: str) -> bool:
        """Check if a tool has a signed certificate."""
        cert = self._cache.get(tool_id)
        if not cert:
            return False
        return bool(cert.signature)

    def update_trust(self, tool_id: str, success: bool) -> Optional[float]:
        """Update trust score for a tool and persist."""
        cert = self._cache.get(tool_id)
        if not cert:
            return None
        new_score = cert.update_trust(success)
        self.save(cert)
        return new_score

    def get_summary(self) -> Dict[str, any]:
        """Get a summary of the trust store."""
        total = len(self._cache)
        signed = sum(1 for c in self._cache.values() if c.signature)
        trusted = sum(1 for c in self._cache.values() if c.trust_score >= 0.6)
        high_risk = sum(1 for c in self._cache.values() if c.risk_profile.level in ("high", "critical"))
        return {
            "total_certificates": total,
            "signed": signed,
            "trusted": trusted,
            "high_risk": high_risk,
            "trust_dir": self._trust_dir,
        }
