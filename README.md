<div align="center">

# 💠 JadeGate

**Deterministic Security for AI Agent Skills**

*"Code is fluid. Jade is solid."*

*以玉为契，不可篡改。*

[![PyPI](https://img.shields.io/pypi/v/jadegate?color=jade&label=pip%20install%20jadegate)](https://pypi.org/project/jadegate/)
[![Skills](https://img.shields.io/badge/skills-101%20verified-jade)](CATALOG.md)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)]()

</div>

---

## What is JadeGate?

**JADE** (JSON-based Agent Deterministic Execution) is a zero-trust security protocol for AI agent skills.

Every skill is a pure JSON file — non-Turing-complete, structurally verifiable, mathematically provable safe.

No `eval()`. No `exec()`. No `import`. No escape.

```
羌笛何须怨杨柳，春风不度玉门关。
Malicious code shall not pass the JadeGate.
```

## Why?

MCP is powerful but permissive. Any MCP server can run arbitrary code. JadeGate adds a security layer:

| | MCP | JadeGate |
|---|---|---|
| Format | Arbitrary code | Pure JSON |
| Verification | Trust the server | 5-layer deterministic proof |
| Signatures | None | Ed25519 chain of trust |
| Sandbox | Server-dependent | Enforced by protocol |
| Dependencies | Runtime-dependent | Zero |

## Quick Start

```bash
pip install jadegate
```

```bash
# Browse all verified skills
jade list

# Search for what you need
jade search "github"

# Check skill details
jade info mcp_brave_search

# Verify any skill file
jade verify my_skill.json

# System status
jade status
```

## 5-Layer Verification

Every skill passes through 5 deterministic security layers:

```
Layer 1: Schema Validation     — Structure must be valid JADE JSON
Layer 2: DAG Integrity         — Execution graph must be acyclic, no loops
Layer 3: Security Policy       — Sandbox, network whitelist, permissions
Layer 4: Injection Detection   — No code injection, no template attacks
Layer 5: Cryptographic Seal    — Ed25519 signature chain verification
```

All layers are deterministic. Same input → same result. Every time.

## Trust Hierarchy

```
💠 Root Seal        — Project authority, highest trust
🔷 Org Seal         — Authorized organizations
🔹 Community Seal   — Anyone can sign; 5+ sigs = Community Verified
```

```bash
# Generate your community signing key
python jade_community_sign.py keygen

# Sign a skill you've reviewed
python jade_community_sign.py sign jade_skills/mcp/mcp_brave_search.json

# Check all signatures on a skill
python jade_community_sign.py check jade_skills/mcp/mcp_brave_search.json
```

## 101 Verified Skills

JadeGate ships with **101 pre-verified skills** across two categories:

### MCP Skills (61)
GitHub, Slack, Discord, OpenAI, Anthropic, AWS, GCP, Firebase, MongoDB, Redis, Elasticsearch, Stripe, Twilio, SendGrid, Jira, Confluence, Vercel, Shopify, and more.

### Tool Skills (40)
CSV analysis, DNS lookup, QR code, image resize, JWT decode, regex tester, password generator, UUID, YAML/JSON converter, and more.

→ Full list: [CATALOG.md](CATALOG.md)

## For AI Agents

All commands support `--json` for machine-readable output:

```bash
jade search --json "web search"
jade list --json --type mcp
jade info --json mcp_brave_search
```

```python
from jade_core.validator import JadeValidator

v = JadeValidator()
result = v.validate_file("my_skill.json")
print(result.valid)  # True/False
print(result.issues) # Detailed security findings
```

## Skill Format

A JadeGate skill is a single JSON file:

```json
{
  "jade_version": "1.0.0",
  "skill_id": "my_skill",
  "metadata": {
    "name": "My Skill",
    "description": "What it does",
    "version": "1.0.0",
    "tags": ["example"]
  },
  "input_schema": { ... },
  "output_schema": { ... },
  "execution_dag": {
    "nodes": [ ... ],
    "edges": [ ... ]
  },
  "security": {
    "sandbox": "strict",
    "network_whitelist": ["api.example.com"],
    "max_execution_time_ms": 10000
  }
}
```

No code. Just structure. Verifiable by anyone.

## Contributing

1. Create a skill JSON file
2. Run `jade verify your_skill.json`
3. Submit a PR — CI auto-verifies
4. Community signs → merged

## Architecture

```
┌─────────────────────────────────────────┐
│              AI Agent                    │
├─────────────────────────────────────────┤
│         JadeGate Protocol               │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Verify  │ │ Search   │ │ Execute  │ │
│  │ 5-Layer │ │ Catalog  │ │ Sandbox  │ │
│  └─────────┘ └──────────┘ └──────────┘ │
├─────────────────────────────────────────┤
│  💠 Ed25519 Signature Chain             │
├─────────────────────────────────────────┤
│  Skills (Pure JSON, no code)            │
└─────────────────────────────────────────┘
```

## License

Apache 2.0

---

<div align="center">

**💠 JadeGate** — *Trust is not assumed. Trust is proven.*

</div>
