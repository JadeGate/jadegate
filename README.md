# JadeGate 💠

**The TLS of AI Tool Calls.**

[![PyPI](https://img.shields.io/pypi/v/jadegate?color=10b981&style=flat-square)](https://pypi.org/project/jadegate/)
[![Tests](https://img.shields.io/badge/tests-238_passing-10b981?style=flat-square)](#running-tests)
[![License](https://img.shields.io/badge/license-BSL_1.1-blue?style=flat-square)](LICENSE)
[![Website](https://img.shields.io/badge/website-jadegate.io-purple?style=flat-square)](https://jadegate.io)

One command. Every MCP server protected. Zero config.

```bash
pip install jadegate
```

<p align="center">
  <img src="assets/demo.gif" alt="JadeGate Demo" width="730">
</p>

---

## Why JadeGate?

MCP has no security layer. Any tool can read your files, make network requests, or execute commands — and your AI client will happily comply.

There are 10,000+ MCP servers on GitHub. Most have never been audited. Security researchers have demonstrated tools that silently access `~/.ssh/`, `.env` files, and browser cookies while claiming to do something harmless.

MCP is TCP without TLS. **JadeGate adds the TLS.**

- 🔒 **Zero config** — `pip install` = protected
- 🔍 **6-layer security** — policy, runtime, transport, trust, scanner, installer
- 🚫 **Zero cloud** — everything runs locally, no telemetry
- 🧮 **Zero LLM** — pure deterministic verification, no token cost
- ↩️ **Fully reversible** — `jadegate uninstall` restores everything

## How It Works

JadeGate sits between your AI client and MCP servers as a transparent proxy:

```
AI Client (Claude, Cursor, etc.)
    ↓
  💠 JadeGate Proxy       ← 6-layer security check
    ↓
  MCP Server (filesystem, github, puppeteer, etc.)
```

<p align="center">
  <img src="assets/pipeline_6layer.png" alt="JadeGate 6-Layer Security Stack" width="730">
</p>

### The 6 Layers

| Layer | What it does |
|-------|-------------|
| **Installer** | Auto-injects into Claude, Cursor, Windsurf, Cline, Continue, Zed configs |
| **Scanner** | Static analysis of MCP server capabilities, risk scoring, capability heatmap |
| **Policy** | Allow/deny/ask rules per tool, rate limiting, argument validation |
| **Runtime** | Dynamic call-chain tracking (DAG), anomaly detection, circuit breaker |
| **Transport** | Transparent MCP proxy — intercepts stdio/SSE without modifying the server |
| **Trust** | TOFU + Ed25519 certificates for server identity verification |

## Quick Start

### 1. Install

```bash
pip install jadegate
```

JadeGate automatically:
1. Scans your system for MCP client configurations
2. Wraps each MCP server with the JadeGate proxy
3. Backs up original configs (fully reversible)

Next time you open Claude Desktop, Cursor, or any supported client — protection is active.

### 2. Check Status

```bash
jadegate status
```

### 3. Scan Your MCP Servers

```bash
jadegate scan
```

Output:
```
💠 JadeGate v2.0.0 — AI Tool Call Security Protocol

MCP Server Security Scan

✓ filesystem  ● MEDIUM    filesystem access
  tools: 3 discovered
✓ github      ● MEDIUM    network access
  tools: 5 discovered
✓ puppeteer   ● CRITICAL  shell + network + browser
  tools: 8 discovered

3 servers scanned: 0 low, 2 medium, 0 high, 1 critical
All servers protected by JadeGate proxy.
```

### 4. Uninstall (if needed)

```bash
jadegate uninstall   # Restores all original configs
pip uninstall jadegate
```

## Python SDK Protection

For Python agents using OpenAI or Anthropic SDKs directly:

```python
import jadegate
jadegate.activate()

# Now use OpenAI/Anthropic as normal — JadeGate intercepts tool calls
from openai import OpenAI
client = OpenAI()
```

Or via environment variable:

```bash
export JADEGATE=1
python my_agent.py
```

## Trust Hierarchy

JadeGate uses Ed25519 signature chains with three trust levels:

<p align="center">
  <img src="assets/trust_hierarchy.png" alt="JadeGate Trust Hierarchy" width="730">
</p>

| Badge | Level | How to get it |
|-------|-------|--------------|
| 💠 Origin | Root CA signed | JadeGate team review |
| 🔷 Organization | Org CA signed | Apply for org certificate |
| 🔹 Community | CI verified | Add `JadeGate/verify-action@v1` to your CI |

### Add the Verified Badge to Your MCP Server

```yaml
# .github/workflows/jadegate.yml
name: JadeGate Verify
on: [push, pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: JadeGate/verify-action@v1
```

Pass all 5 checks → get the 🔹 Community Verified badge automatically.

## Policy Configuration

Default policy blocks dangerous patterns. Customize per tool:

```json
{
  "default_action": "allow",
  "tool_rules": {
    "filesystem:write_file": {
      "action": "ask",
      "reason": "File write requires confirmation"
    },
    "shell:exec": {
      "action": "deny",
      "reason": "Shell execution blocked by policy"
    }
  },
  "rate_limit": {
    "max_calls_per_minute": 60
  }
}
```

## Supported Clients

| Client | Auto-detected |
|--------|:---:|
| Claude Desktop | ✅ |
| Cursor | ✅ |
| Windsurf | ✅ |
| Cline (VS Code) | ✅ |
| Continue | ✅ |
| Zed | ✅ |
| Custom | `jadegate install --config <path>` |

## Comparison

<p align="center">
  <img src="assets/mcp_vs_jadegate.png" alt="MCP vs JadeGate" width="730">
</p>

## Running Tests

```bash
pip install pytest
pytest tests/ -v
# 238 tests, all passing
```

## Design Principles

- **Zero config**: `pip install` = protected. No setup, no env vars, no config files.
- **Transparent**: MCP servers don't know JadeGate exists. No server-side changes.
- **Reversible**: `jadegate uninstall` restores everything. Clean removal guaranteed.
- **Offline**: All analysis runs locally. No telemetry, no cloud, no data leaves your machine.
- **Deterministic**: Pure math verification. No LLM calls, no heuristics, no false positives.
- **Fail-open safe**: If JadeGate crashes, your MCP servers still work.

## License

[BSL 1.1](LICENSE) — Converts to Apache 2.0 on 2030-02-01.

Free for non-production use. Production use requires a commercial license until the conversion date.

---

💠 **[jadegate.io](https://jadegate.io)** · [GitHub](https://github.com/JadeGate/jadegate) · [PyPI](https://pypi.org/project/jadegate/) · [Discord](https://discord.gg/clawd)
