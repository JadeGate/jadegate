<div align="center">

# 💠 JadeGate

### *Deterministic Security for AI Agent Skills*

**"Code is fluid. Jade is solid."**

**以玉为契，不可篡改。**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Skills](https://img.shields.io/badge/Skills-35-blue.svg)](#skill-registry)
[![Schema](https://img.shields.io/badge/Schema-v1.0-purple.svg)](#jade-schema)
[![crates.io](https://img.shields.io/crates/v/jadegate.svg)](https://crates.io/crates/jadegate)

---

*羌笛何须怨杨柳，春风不度玉门关。*

*Malicious code shall not pass the JadeGate.*

</div>

---

## What is JADE?

**JADE** (JSON-based Agent Deterministic Execution) is a zero-trust security protocol for AI Agent skills.

Every skill is a pure JSON file — non-Turing-complete, structurally verifiable, mathematically provable safe.

No `eval()`. No `exec()`. No `import`. No exceptions.

```
💠 JADE Verified    — Passed all 5 security layers
❌ Rejected          — Blocked: executable code / dangerous patterns detected
```

## Why JADE?

Traditional AI skills (Markdown files, Python scripts) are **inherently unsafe**:
- They can contain hidden executable code
- They can exfiltrate private data
- They can be prompt-injected

JADE makes safety a **structural property**, not a behavioral one:

| | Traditional Skills | JADE Skills |
|---|---|---|
| Format | Markdown / Python | Pure JSON (non-Turing-complete) |
| Safety | Review-based (hope for the best) | Structural (mathematically proven) |
| Verification | Manual | Automated 5-layer validation |
| Execution | Arbitrary code | Deterministic DAG |

## 5-Layer Security Validation

```
Layer 1: JSON Schema — structural integrity
Layer 2: Code Injection — 22 executable patterns blocked
Layer 3: Dangerous Commands — 25+ system commands blocked  
Layer 4: Network & Data — whitelist enforcement + data leak prevention
Layer 5: DAG Safety — cycle detection + reachability proof
```

All layers pass = 💠. Any layer fails = ❌.

## Install

```bash
# Python
pip install jadegate

# Rust
cargo add jadegate
```

## Quick Start

```python
from jade_core.validator import JadeValidator
from jade_core.client import JadeClient

# Validate a skill
validator = JadeValidator()
result = validator.validate_file("jade_skills/weather_api.json")
print(f"Valid: {result.valid}")  # True

# Load and use skills
client = JadeClient()
skill = client.load_file("jade_skills/weather_api.json")
print(skill.execution_dag.entry_node)
```

## Skill Registry

35 verified skills across 8 categories:

| Category | Skills | Examples |
|----------|--------|---------|
| 🌐 Web & Search | 6 | web_search, webpage_screenshot, rss_reader |
| 📡 API Integration | 5 | notion, github, exa, slack, discord |
| 🔧 System & DevOps | 6 | git_clone, docker, ssh, sqlite, shell |
| 📁 File Operations | 4 | file_rename, csv_analysis, pdf_parser, hash_verify |
| 🔒 Network & Security | 5 | dns_lookup, ssl_check, whois, health_check, ip_geo |
| 💬 Messaging | 3 | slack, discord, telegram |
| 🧠 AI & NLP | 3 | translation, sentiment, content_extract |
| 🛠️ Utilities | 3 | timezone, qr_code, base64, json_transform |

## Architecture

```
┌─────────────────────────────────────────┐
│           JADE Skill (JSON)             │
│  ┌─────────┐  ┌──────┐  ┌───────────┐  │
│  │ Trigger  │→ │ DAG  │→ │  Output   │  │
│  └─────────┘  └──────┘  └───────────┘  │
└──────────────────┬──────────────────────┘
                   │ validate
┌──────────────────▼──────────────────────┐
│          JadeValidator (5 layers)        │
│  Schema → Injection → Commands →        │
│  Network → DAG Safety                   │
└──────────────────┬──────────────────────┘
                   │
            💠 or ❌
```

## MCP Compatible

JADE skills are fully compatible with the [Model Context Protocol](https://modelcontextprotocol.io/). Use JADE as the security layer on top of MCP:

> *"Use MCP to connect. Use JADE to protect."*

## Project Structure

```
jade-core/
├── jade_core/          # Core Python library
│   ├── validator.py    # 5-layer security validator
│   ├── security.py     # Zero-trust security engine
│   ├── dag.py          # DAG analyzer
│   ├── client.py       # Client SDK
│   ├── registry.py     # Bayesian confidence registry
│   └── models.py       # Data models
├── jade_schema/        # JSON Schema + allowed actions
├── jade_skills/        # Official verified skills (💠)
├── converted_skills/   # Community skills (✅)
├── jade_registry/      # Skill index
├── tests/              # 135 test cases
└── tools/              # Converters and utilities
```

## Roadmap

- [x] v0.1 — Core validator + 35 skills + schema
- [ ] v0.2 — `jade list` / `jade verify` / `jade install` CLI
- [ ] v0.3 — Cryptographic signing (🔏 JADE Sealed)
- [ ] v0.4 — Bayesian trust routing + global attestation network
- [ ] v0.5 — Rust client for 10ms verification

## Contributing

We welcome skill contributions! Every submitted skill must pass all 5 validation layers.

```bash
# Validate your skill before submitting
python -c "
from jade_core.validator import JadeValidator
v = JadeValidator()
r = v.validate_file('your_skill.json')
print('💠 Verified' if r.valid else '❌ Rejected')
for i in r.errors: print(f'  {i.message}')
"
```

## License

MIT — Free to use, free to build on.

---

<div align="center">

**💠 JadeGate** — *Pass the Gate. Trust the Jade.*

[GitHub](https://github.com/JadeGate) · [PyPI](https://pypi.org/project/jadegate/) · [crates.io](https://crates.io/crates/jadegate) · [Skills](./jade_skills/) · [Schema](./jade_schema/)

</div>
