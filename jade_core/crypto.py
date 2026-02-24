"""
JadeGate Cryptographic Engine — Ed25519 Pure Python Implementation

⚠️ SECURITY NOTE: This is a pure-Python Ed25519 implementation for zero-dependency operation.
For production environments handling high-value signatures, consider using the `cryptography` library
(pip install cryptography) which provides constant-time C implementations.
This implementation uses hmac.compare_digest for timing-safe comparisons.

This is the "权柄" (authority scepter) of JadeGate.
Root CA private key holder can:
  - Sign any skill file (root-level certification)
  - Issue organization sub-CA certificates
  - Revoke any issued certificate

Algorithm: Ed25519 (same as SSH, Signal, Tor)
Key format: jade-sk-{role}-{base64} / jade-pk-{role}-{base64}
Signature format: jade-sig-{base64}
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import base64
import datetime
from typing import Optional, Dict, Any, Tuple


# ============================================================
# Ed25519 Pure Python (no external dependencies)
# Reference: RFC 8032
# ============================================================

b = 256
q = 2**255 - 19
l_order = 2**252 + 27742317777372353535851937790883648493


def _H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()


def _expmod(b_val: int, e: int, m: int) -> int:
    if e == 0:
        return 1
    t = _expmod(b_val, e // 2, m) ** 2 % m
    if e & 1:
        t = (t * b_val) % m
    return t


def _inv(x: int) -> int:
    return _expmod(x, q - 2, q)


_d = -121665 * _inv(121666) % q
_I = _expmod(2, (q - 1) // 4, q)


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = _expmod(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * _I) % q
    if x % 2 != 0:
        x = q - x
    return x


_By = 4 * _inv(5)
_Bx = _xrecover(_By)
_B = [_Bx % q, _By % q]


def _edwards(P: list, Q: list) -> list:
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + _d * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - _d * x1 * x2 * y1 * y2)
    return [x3 % q, y3 % q]


def _scalarmult(P: list, e: int) -> list:
    if e == 0:
        return [0, 1]
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1:
        Q = _edwards(Q, P)
    return Q


def _encodeint(y: int) -> bytes:
    bits = [(y >> i) & 1 for i in range(b)]
    return bytes([sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8)])


def _encodepoint(P: list) -> bytes:
    x, y = P
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return bytes([sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8)])


def _bit(h: bytes, i: int) -> int:
    return (h[i // 8] >> (i % 8)) & 1


def _publickey(sk: bytes) -> bytes:
    h = _H(sk)
    a = 2 ** (b - 2) + sum(2**i * _bit(h, i) for i in range(3, b - 2))
    A = _scalarmult(_B, a)
    return _encodepoint(A)


def _Hint(m: bytes) -> int:
    h = _H(m)
    return sum(2**i * _bit(h, i) for i in range(2 * b))


def _signature(m: bytes, sk: bytes, pk: bytes) -> bytes:
    h = _H(sk)
    a = 2 ** (b - 2) + sum(2**i * _bit(h, i) for i in range(3, b - 2))
    r = _Hint(bytes([h[j] for j in range(b // 8, b // 4)]) + m)
    R = _scalarmult(_B, r)
    S = (r + _Hint(_encodepoint(R) + pk + m) * a) % l_order
    return _encodepoint(R) + _encodeint(S)


def _isoncurve(P: list) -> bool:
    x, y = P
    return (-x * x + y * y - 1 - _d * x * x * y * y) % q == 0


def _decodeint(s: bytes) -> int:
    return sum(2**i * _bit(s, i) for i in range(0, b))


def _decodepoint(s: bytes) -> list:
    y = sum(2**i * _bit(s, i) for i in range(0, b - 1))
    x = _xrecover(y)
    if x & 1 != _bit(s, b - 1):
        x = q - x
    P = [x, y]
    if not _isoncurve(P):
        raise ValueError("decoding point that is not on curve")
    return P


def _checkvalid(s: bytes, m: bytes, pk: bytes) -> bool:
    if len(s) != b // 4:
        raise ValueError("signature length is wrong")
    if len(pk) != b // 8:
        raise ValueError("public-key length is wrong")
    R = _decodepoint(s[0:b // 8])
    A = _decodepoint(pk)
    S = _decodeint(s[b // 8:b // 4])
    h = _Hint(_encodepoint(R) + pk + m)
    # Constant-time comparison to prevent timing attacks
    lhs = _encodepoint(_scalarmult(_B, S))
    rhs = _encodepoint(_edwards(R, _scalarmult(A, h)))
    if not hmac.compare_digest(lhs, rhs):
        return False
    return True


# ============================================================
# High-level JadeGate Crypto API
# ============================================================

class JadeKeyPair:
    """An Ed25519 keypair with JadeGate formatting."""

    def __init__(self, seed: bytes, role: str = "root"):
        self.seed = seed
        self.role = role
        self.public_key_bytes = _publickey(seed)

    @classmethod
    def generate(cls, role: str = "root") -> "JadeKeyPair":
        seed = os.urandom(32)
        return cls(seed, role)

    @classmethod
    def from_private_key(cls, key_str: str) -> "JadeKeyPair":
        if not key_str.startswith("jade-sk-"):
            raise ValueError("Invalid key format. Expected jade-sk-{role}-{base64}")
        # Format: jade-sk-{role}-{base64} where base64 always ends with =
        # Role can contain dashes (e.g. org-alibaba-cloud)
        # Strategy: base64 is always the last segment after the last dash before =
        prefix = key_str[len("jade-sk-"):]  # strip "jade-sk-"
        # Format: {role}-{base64} where role may contain dashes
        # base64 of 32 bytes = 44 chars, use rfind to get last dash
        last_dash = prefix.rfind("-")
        if last_dash == -1:
            raise ValueError("Invalid key format")
        role = prefix[:last_dash]
        b64_str = prefix[last_dash + 1:]
        seed = base64.b64decode(b64_str)
        if len(seed) != 32:
            raise ValueError("Invalid key length")
        return cls(seed, role)

    @property
    def private_key_str(self) -> str:
        return f"jade-sk-{self.role}-{base64.b64encode(self.seed).decode()}"

    @property
    def public_key_str(self) -> str:
        return f"jade-pk-{self.role}-{base64.b64encode(self.public_key_bytes).decode()}"

    @property
    def fingerprint(self) -> str:
        fp = base64.b64encode(hashlib.sha256(self.public_key_bytes).digest()).decode()
        return f"SHA256:{fp}"

    def sign(self, message: bytes) -> str:
        sig = _signature(message, self.seed, self.public_key_bytes)
        return f"jade-sig-{base64.b64encode(sig).decode()}"

    @staticmethod
    def verify(message: bytes, signature_str: str, public_key_str: str) -> bool:
        if not signature_str.startswith("jade-sig-"):
            raise ValueError("Invalid signature format")
        if not public_key_str.startswith("jade-pk-"):
            raise ValueError("Invalid public key format")
        # sig format: jade-sig-{base64}
        sig_b64 = signature_str[len("jade-sig-"):]
        sig_bytes = base64.b64decode(sig_b64)
        # pk format: jade-pk-{role}-{base64} where role may contain dashes
        # base64 of 32 bytes = 44 chars, always ends with = or has specific length
        pk_prefix = public_key_str[len("jade-pk-"):]
        # Find last segment that is valid base64 (44 chars for 32-byte key)
        last_dash = pk_prefix.rfind("-")
        pk_b64 = pk_prefix[last_dash + 1:]
        pk_bytes = base64.b64decode(pk_b64)
        try:
            return _checkvalid(sig_bytes, message, pk_bytes)
        except Exception:
            return False


class JadeSkillSigner:
    """Sign and verify JADE skill files."""

    def __init__(self, keypair: Optional[JadeKeyPair] = None):
        self.keypair = keypair

    def sign_skill(self, skill_path: str) -> Dict[str, Any]:
        """Sign a skill file. Returns the signature envelope."""
        if not self.keypair:
            raise ValueError("No keypair loaded. Cannot sign.")

        with open(skill_path, 'r') as f:
            skill_data = f.read()

        # Canonical JSON (sorted keys, no extra whitespace, strip old signature)
        skill_json = json.loads(skill_data)
        skill_clean = {k: v for k, v in skill_json.items() if k != "jade_signature"}
        canonical = json.dumps(skill_clean, sort_keys=True, separators=(',', ':'))
        content_hash = hashlib.sha256(canonical.encode()).hexdigest()

        # Sign the content hash
        signature = self.keypair.sign(content_hash.encode())

        # Build signature envelope
        envelope = {
            "jade_signature": {
                "version": "1.0.0",
                "skill_id": skill_json.get("skill_id", "unknown"),
                "content_hash": f"sha256:{content_hash}",
                "signature": signature,
                "signer": {
                    "public_key": self.keypair.public_key_str,
                    "fingerprint": self.keypair.fingerprint,
                    "role": self.keypair.role,
                },
                "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "expires": (datetime.datetime.utcnow() + datetime.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        }

        # Write signature file alongside skill
        sig_path = skill_path.replace('.json', '.sig.json')
        with open(sig_path, 'w') as f:
            json.dump(envelope, f, indent=2)

        # Also embed signature in skill file
        skill_json["jade_signature"] = envelope["jade_signature"]
        with open(skill_path, 'w') as f:
            json.dump(skill_json, f, indent=2)

        return envelope

    @staticmethod
    def verify_skill(skill_path: str, trusted_keys: Optional[list] = None) -> Dict[str, Any]:
        """Verify a signed skill file. Returns verification result."""
        with open(skill_path, 'r') as f:
            skill_json = json.load(f)

        sig_info = skill_json.get("jade_signature")
        if not sig_info:
            # Try external .sig.json
            sig_path = skill_path.replace('.json', '.sig.json')
            if os.path.exists(sig_path):
                with open(sig_path, 'r') as f:
                    sig_info = json.load(f).get("jade_signature")

        if not sig_info:
            return {"verified": False, "error": "No signature found", "signed": False}

        # Reconstruct canonical content (without signature)
        skill_copy = {k: v for k, v in skill_json.items() if k != "jade_signature"}
        canonical = json.dumps(skill_copy, sort_keys=True, separators=(',', ':'))
        content_hash = hashlib.sha256(canonical.encode()).hexdigest()

        # Check content hash
        expected_hash = sig_info.get("content_hash", "")
        if not hmac.compare_digest(expected_hash, f"sha256:{content_hash}"):
            return {"verified": False, "error": "Content hash mismatch — skill was tampered", "signed": True}

        # Verify signature
        signature = sig_info.get("signature", "")
        public_key = sig_info["signer"]["public_key"]

        # Check against trusted keys if provided
        if trusted_keys:
            fingerprint = sig_info["signer"]["fingerprint"]
            if fingerprint not in trusted_keys and public_key not in trusted_keys:
                return {"verified": False, "error": f"Signer {fingerprint} not in trusted keys", "signed": True}

        try:
            valid = JadeKeyPair.verify(content_hash.encode(), signature, public_key)
        except Exception as e:
            return {"verified": False, "error": f"Signature verification failed: {e}", "signed": True}

        if not valid:
            return {"verified": False, "error": "Invalid signature", "signed": True}

        # Check expiry
        expires = sig_info.get("expires", "")
        if expires:
            try:
                exp_dt = datetime.datetime.strptime(expires, "%Y-%m-%dT%H:%M:%SZ")
                if datetime.datetime.utcnow() > exp_dt:
                    return {"verified": False, "error": "Signature expired", "signed": True}
            except ValueError:
                pass

        return {
            "verified": True,
            "signed": True,
            "signer": sig_info["signer"],
            "timestamp": sig_info.get("timestamp"),
            "expires": sig_info.get("expires"),
            "content_hash": sig_info.get("content_hash"),
        }


class JadeOrgCA:
    """Issue and manage organization sub-CA certificates."""

    def __init__(self, root_keypair: JadeKeyPair):
        if root_keypair.role != "root":
            raise ValueError("Only root CA can issue org certificates")
        self.root = root_keypair

    def issue_org_cert(self, org_id: str, org_name: str, badge_text: str,
                       badge_icon: str = "💠", badge_color: str = "#10b981",
                       validity_days: int = 365) -> Dict[str, Any]:
        """Issue a sub-CA certificate for an organization."""
        # Generate org keypair
        org_kp = JadeKeyPair.generate(role=f"org-{org_id}")

        # Build certificate
        cert_data = {
            "org_id": org_id,
            "org_name": org_name,
            "public_key": org_kp.public_key_str,
            "fingerprint": org_kp.fingerprint,
        }
        cert_canonical = json.dumps(cert_data, sort_keys=True, separators=(',', ':'))

        # Root CA signs the org cert
        root_sig = self.root.sign(cert_canonical.encode())

        cert = {
            "jade_org_certificate": {
                "version": "1.0.0",
                "org_id": org_id,
                "display_name": org_name,
                "badge_text": badge_text,
                "badge_icon": badge_icon,
                "badge_color": badge_color,
                "public_key": org_kp.public_key_str,
                "fingerprint": org_kp.fingerprint,
                "issuer": {
                    "public_key": self.root.public_key_str,
                    "fingerprint": self.root.fingerprint,
                    "role": "root",
                },
                "root_signature": root_sig,
                "issued": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "expires": (datetime.datetime.utcnow() + datetime.timedelta(days=validity_days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "permissions": ["sign:skill"],
            }
        }

        return {
            "certificate": cert,
            "org_private_key": org_kp.private_key_str,
            "org_public_key": org_kp.public_key_str,
            "org_fingerprint": org_kp.fingerprint,
        }

    def verify_org_cert(self, cert: Dict[str, Any]) -> bool:
        """Verify an org certificate was signed by root CA."""
        org_cert = cert.get("jade_org_certificate", cert)
        cert_data = {
            "org_id": org_cert["org_id"],
            "org_name": org_cert["display_name"],
            "public_key": org_cert["public_key"],
            "fingerprint": org_cert["fingerprint"],
        }
        cert_canonical = json.dumps(cert_data, sort_keys=True, separators=(',', ':'))
        root_sig = org_cert["root_signature"]
        root_pk = org_cert["issuer"]["public_key"]

        return JadeKeyPair.verify(cert_canonical.encode(), root_sig, root_pk)
