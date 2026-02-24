# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in JadeGate, please report it responsibly.

**Email:** security@jadegate.io

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

We will acknowledge receipt within 48 hours and provide a fix timeline within 7 days.

**Do NOT open a public GitHub issue for security vulnerabilities.**

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x.x   | ✅        |
| < 1.0   | ❌        |

## Security Design

JadeGate's security is based on:
- Non-Turing-complete skill format (pure JSON, no executable code)
- 5-layer deterministic verification
- Ed25519 cryptographic signatures
- Zero external dependencies in core
- Offline-first (no network required)
