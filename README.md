<div align="center">

# 💠 JadeGate

**Deterministic Security for AI Agent Skills**

*春风不度玉门关*

[![License: BSL 1.1](https://img.shields.io/badge/License-BSL_1.1-blue.svg)](#license)
[![PyPI](https://img.shields.io/pypi/v/jadegate.svg)](https://pypi.org/project/jadegate/)
[![crates.io](https://img.shields.io/crates/v/jadegate.svg)](https://crates.io/crates/jadegate)
[![Skills](https://img.shields.io/badge/Verified_Skills-35-blue.svg)](#skill-registry)
[![Schema](https://img.shields.io/badge/Schema-v1.0-purple.svg)](#jade-schema)

**中文** | [English](#english-docs)

</div>

---

<div align="center">

# 💠 JadeGate 中文文档

**AI 智能体技能的确定性安全验证**

*春风不度玉门关*

</div>

## JadeGate 是什么？

JadeGate 是 AI 智能体技能的安全验证层。它对智能体使用的技能文件进行验证、认证和管理，确保技能在执行前是安全的。

**不绑定任何框架。** JadeGate 是纯粹的验证层。OpenClaw、Claude Code、OpenCode、Cursor、LangChain、CrewAI，或者任何 MCP 兼容客户端，都能直接用。

```bash
pip install jadegate
jade verify your_skill.json
```

两行命令，搞定 AI 智能体安全。

## 为什么需要 JadeGate？

AI 智能体的技能（工具、插件、MCP 服务器）本质上就是代码——代码可以是恶意的。一个技能文件可能：

- 💉 注入隐藏的可执行代码
- 📡 把敏感数据偷偷发到未知服务器
- 🔄 通过循环依赖制造死循环
- 🎭 把提示词注入伪装成正常操作

JadeGate 通过 5 层确定性安全验证消除这些攻击面。不靠猜测，不靠 AI 检测，纯数学验证。

## 5 层安全验证

| 层级 | 验证内容 | 方法 |
|------|---------|------|
| 第 1 层 | 结构完整性 | JSON Schema 严格校验 |
| 第 2 层 | 代码注入扫描 | 47 种注入模式匹配 |
| 第 3 层 | 贝叶斯置信度 | 多层证据贝叶斯推断，≥0.95 通过 |
| 第 4 层 | 网络泄露分析 | 域名白名单 + 协议审查 |
| 第 5 层 | DAG 完整性 | DFS 环检测 + 可达性证明 + 终止保证 |

## 信任模型

JadeGate 使用非对称加密进行技能认证：

- **所有者** 持有私钥（`jade-sk-...`），绝不公开
- **公钥** 发布在仓库中（`jadegate.pub.json`）
- 经所有者签名的技能获得 💠 认证
- 任何人都能验证签名，但只有所有者能签发
- 支持密钥轮换，旧签名依然有效

这和 npm、PyPI 等包管理器以及 CA 证书机构使用的信任模型一致。

## CLI 命令

```bash
jade list              # 列出所有已验证技能
jade verify skill.json # 验证技能文件（5 层报告）
jade search "天气"      # 搜索技能
jade info <skill_id>   # 查看技能详情
jade key generate      # 生成密钥对
jade key rotate        # 轮换密钥
jade key show          # 查看当前密钥
jade key export        # 导出公钥
```

## 安装

```bash
pip install jadegate     # Python
cargo add jadegate       # Rust
```

---

<div align="center">

**💠 JadeGate** — *Pass the Gate. Trust the Jade.*

[GitHub](https://github.com/JadeGate/jade-core) · [PyPI](https://pypi.org/project/jadegate/) · [crates.io](https://crates.io/crates/jadegate)

</div>


<div id="english-docs"></div>

## What is JadeGate?

JadeGate is a deterministic security layer for AI agent skills. It validates, certifies, and manages skill files that AI agents use — ensuring they are safe before execution.

**Framework-agnostic by design.** JadeGate is a pure verification layer. It doesn't bind to any framework. OpenClaw, Claude Code, OpenCode, Cursor, LangChain, CrewAI, or any MCP-compatible client — all work out of the box.

```bash
pip install jadegate
jade verify your_skill.json
```

That's it. Two lines to secure your AI agent.

## Why JadeGate?

AI agent skills (tools, plugins, MCP servers) are just code — and code can be malicious. A skill file could:

- 💉 Inject hidden executable code
- 📡 Exfiltrate sensitive data to unknown servers
- 🔄 Create infinite loops via circular dependencies
- 🎭 Disguise prompt injection as legitimate operations

JadeGate eliminates these attack vectors through 5 deterministic security layers. No heuristics. No AI-based detection. Pure mathematical verification.

## Verification States

```
💠 Verified  — Passed all 5 security layers
⚠️  Warning   — Passed with risk flags (broad permissions, unknown domains)
🔒 Locked    — Signature expired or revoked
❌ Rejected  — Structural violation, refused to load
```

## The 5 Security Layers

### Layer 1: Structural Integrity (JSON Schema)
Validates skill files against the JADE schema. Malformed files are rejected before any further analysis.

### Layer 2: Code Injection Scan
Pattern-matches against 47 known injection vectors: `eval()`, `exec()`, `__import__()`, template literals, encoded payloads, and more. A single match → ❌ Rejected.

### Layer 3: Bayesian Confidence Scoring

Each layer produces a binary pass/fail signal. The final confidence score is computed via Bayesian inference:

```
P(safe | evidence) = ∏ P(eᵢ | safe) · P(safe) / P(evidence)
```

Where:
- `P(eᵢ | safe)` = likelihood of layer i passing given a safe skill
- `P(safe)` = prior (default: 0.5, updated per-registry)
- Confidence ≥ 0.95 → 💠 Verified
- Confidence 0.70–0.95 → ⚠️ Warning
- Confidence < 0.70 → ❌ Rejected

### Layer 4: Network & Data Leak Analysis
Whitelists permitted domains and protocols. Any outbound connection to an unlisted endpoint → flagged or rejected.

### Layer 5: DAG Integrity Verification

Skills define execution flows as Directed Acyclic Graphs. JadeGate verifies:

- **Cycle detection** via DFS with coloring (White → Gray → Black)
- **Reachability proof** — all nodes reachable from entry
- **Termination guarantee** — DAG structure ensures finite execution

```
G = (V, E) where:
  V = {operation nodes}
  E = {dependency edges}
  ∀ v ∈ V: ∃ path(entry, v)  ∧  ¬∃ cycle(G)
```

## CLI

```bash
# List all verified skills with progress bar
jade list

# Verify a skill file (5-layer report)
jade verify skill.json

# Search skills by keyword
jade search "weather"

# Show skill details
jade info weather_api_query

# Key management
jade key generate    # Generate owner keypair
jade key rotate      # Rotate key (old keys archived)
jade key show        # Show current key info
jade key export      # Export public key
```

## Python SDK

```python
from jade_core.validator import JadeValidator
from jade_core.client import JadeClient

# Validate
validator = JadeValidator()
result = validator.validate_file("skill.json")
print(f"Valid: {result.valid}")
print(f"Confidence: {result.confidence:.4f}")

# Load and use
client = JadeClient()
skill = client.load_file("skill.json")
print(skill.execution_dag.entry_node)
```

## Framework Integration

JadeGate works with any AI agent framework:

```python
# OpenClaw / Claude Code / Any MCP client
from jade_core.validator import JadeValidator

validator = JadeValidator()

def load_skill_safely(path):
    result = validator.validate_file(path)
    if not result.valid:
        raise SecurityError(f"Skill rejected: {result.reason}")
    return result.skill
```

```bash
# CI/CD pipeline — one line
jade verify skills/*.json || exit 1
```

```bash
# Rust projects
cargo add jadegate
```

## Trust Model

JadeGate uses a hierarchical certificate authority (CA) model — the same architecture that secures the entire internet (HTTPS/TLS).

### Root CA (Owner)

```
🔑 Root CA — You
│
├── 💠 Directly certify official skills
├── 🏢 Issue Sub-CA certificates to enterprises/labs
│   ├── ✅ They can certify skills within their scope
│   └── ❌ They CANNOT forge root signatures
└── 🚫 Revoke any Sub-CA at any time
```

- The **root private key** (`jade-sk-...`) is held exclusively by the project owner
- The **root public key** is published in `jadegate.pub.json`
- All trust chains terminate at the root — no exceptions

### Sub-CA (Enterprise / Lab)

Organizations can apply for a Sub-CA certificate to certify skills within their own ecosystem:

```bash
# Owner issues a Sub-CA certificate
jade ca issue --org "Anthropic" --scope "claude.*" --expires 365d

# Enterprise uses their Sub-CA to sign skills
jade sign skill.json --key enterprise-sk-...

# Anyone can verify the full chain
jade verify skill.json
# → 💠 Verified (signed by Anthropic, chain → JadeGate Root CA)
```

Sub-CA certificates:
- Are scoped (e.g., only `claude.*` namespace)
- Have expiration dates
- Can be revoked by the root at any time
- Cannot issue further Sub-CAs (depth = 1)

### Signature Enforcement

Starting from v0.2.0, JadeGate supports **strict mode**:

```python
validator = JadeValidator(strict_mode=True)
# Unsigned skills → ❌ Rejected (not just Warning)
```

```bash
jade verify skill.json --strict
# Unsigned → ❌ Rejected
```

| Mode | Unsigned Skill | Signed (valid) | Signed (expired) |
|------|---------------|----------------|-------------------|
| Default | ⚠️ Warning | 💠 Verified | 🔒 Locked |
| Strict | ❌ Rejected | 💠 Verified | 🔒 Locked |

**Recommendation:** All production deployments should enable strict mode.

### Why Fork Won't Help

The code is BSL 1.1-licensed — anyone can fork it. But:

1. **They can't forge your signature.** Without the root private key, they cannot issue 💠 certifications that trace back to JadeGate.
2. **The official registry is yours.** `jadegate.io` is the canonical source of truth for skill trust scores.
3. **Network effect.** Once hundreds of skills are certified under your root key, the switching cost is prohibitive.

This is the same trust model used by certificate authorities (DigiCert, Let's Encrypt), package managers (npm, PyPI), and mobile app stores (Apple, Google).


## Skill Registry

35 verified skills across 8 categories:

| Category | Skills | Examples |
|----------|--------|----------|
| Web & API | 8 | HTTP requests, web scraping, DNS lookup |
| File & System | 6 | File read/write, directory ops, process management |
| Data & Transform | 5 | JSON/CSV/XML parsing, text processing |
| Git & Code | 5 | Clone, diff, commit, branch management |
| Security | 4 | Hash verification, encryption, vulnerability scan |
| Network | 3 | Ping, traceroute, port scan |
| Media | 2 | Image processing, screenshot capture |
| Utility | 2 | Weather API, WHOIS lookup |

## Project Structure

```
jade-core/
├── jade_core/          # Python SDK + CLI
│   ├── cli.py          # jade command-line tool
│   ├── validator.py    # 5-layer verification engine
│   ├── client.py       # Skill loader
│   └── schema.py       # JADE schema definitions
├── jade_schema/        # JSON Schema v1.0
├── jade_skills/        # 35 verified skill definitions
├── jade_registry/      # Skill metadata + search index
├── tests/              # 135 test cases
└── tools/              # Converters and utilities
```

## Contributing

We welcome skill contributions. Every submitted skill must pass all 5 security layers:

```bash
jade verify your_skill.json
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

[BSL 1.1](./LICENSE)

---

