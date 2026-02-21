<div align="center">

# 💠 JadeGate

**Deterministic Security for AI Agent Skills**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/jadegate.svg)](https://pypi.org/project/jadegate/)
[![crates.io](https://img.shields.io/crates/v/jadegate.svg)](https://crates.io/crates/jadegate)
[![Skills](https://img.shields.io/badge/Verified_Skills-35-blue.svg)](#skill-registry)
[![Tests](https://img.shields.io/badge/Tests-135_passed-brightgreen.svg)](#testing)

*

*春风不度玉门关*

[Install](#install) · [Quick Start](#quick-start) · [CLI](#cli) · [Architecture](#architecture) · [Math](#formal-verification) · [Contributing](#contributing)

</div>

---

## Overview

JadeGate is a zero-trust security protocol for AI Agent skills. It defines skills as pure JSON files — non-Turing-complete, structurally verifiable, and deterministically executable.

Traditional agent skills (Markdown, Python, YAML) can contain hidden executable code, exfiltrate data, or be prompt-injected. JadeGate eliminates these attack vectors by design: if it's not valid JSON conforming to the JADE schema, it doesn't run.

```
💠 Verified    — Passed all 5 security layers
⚠️  Warning     — Passed with risk flags (broad permissions, unknown domains)
🔒 Locked      — Signature expired or revoked
❌ Rejected     — Structural violation, refused to load
```

## Why JadeGate

| | Traditional Skills | JADE Skills |
|---|---|---|
| Format | Markdown / Python / YAML | Pure JSON (non-Turing-complete) |
| Safety model | Review-based | Structural (provably safe) |
| Verification | Manual audit | Automated 5-layer validation |
| Execution model | Arbitrary code | Deterministic DAG |
| Attack surface | Unbounded | Formally bounded |

## Install

```bash
pip install jadegate
```

```bash
cargo add jadegate
```

## Quick Start

### Python

```python
from jade_core.validator import JadeValidator

validator = JadeValidator()
result = validator.validate_file("skills/weather_api.json")

if result.valid:
    print("💠 Verified")
else:
    for error in result.errors:
        print(f"❌ [{error.code}] {error.message}")
```

### CLI

```bash
# List all registered skills with trust status
jade list

# Verify a skill file
jade verify skill.json

# Verify all skills in a directory
jade verify ./skills/

# Show detailed security report
jade verify skill.json --verbose

# Search skills by keyword
jade search "weather"
```

Example output:

```
$ jade list
💠 JadeGate Skill Registry — 35 skills, 61 atomic actions

  💠 weather_api           v1.0.0  [web, api, weather]        jade.core
  💠 email_send_safe       v1.0.0  [email, smtp, send]        jade.core
  💠 git_clone_repo        v1.0.0  [git, clone, vcs]          jadegate.community
  💠 dns_lookup            v1.0.0  [dns, lookup, network]     jadegate.community
  💠 ssh_remote_exec       v1.0.0  [ssh, remote, command]     jadegate.community
  ...

$ jade verify my_skill.json
💠 JadeGate Security Validator v1.0

  Layer 1: JSON Schema .............. ✅ PASS
  Layer 2: Code Injection Scan ...... ✅ PASS (22 patterns checked)
  Layer 3: Dangerous Commands ....... ✅ PASS (25 patterns checked)
  Layer 4: Network & Data Leak ...... ✅ PASS (whitelist: api.example.com)
  Layer 5: DAG Integrity ............ ✅ PASS (6 nodes, 0 cycles, all reachable)

  Result: 💠 VERIFIED
  Confidence: 0.94 (Bayesian posterior)
```

## Architecture

```
                    ┌──────────────────────┐
                    │   Agent Framework    │
                    │ (OpenClaw, Claude,   │
                    │  Cursor, MCP, etc.)  │
                    └──────────┬───────────┘
                               │ load skill
                    ┌──────────▼───────────┐
                    │    JadeGate SDK      │
                    │  validate → execute  │
                    └──────────┬───────────┘
                               │
              ┌────────────────▼────────────────┐
              │      5-Layer Security Engine     │
              │                                  │
              │  L1  JSON Schema Validation      │
              │  L2  Code Injection Detection    │
              │  L3  Dangerous Command Blocking  │
              │  L4  Network & Data Leak Guard   │
              │  L5  DAG Integrity Verification  │
              └────────────────┬────────────────┘
                               │
                        💠 or ❌
```

### Framework Integration

JadeGate is framework-agnostic. It works as a security middleware layer:

```python
# OpenClaw / Claude Code / Any MCP client
from jade_core.validator import JadeValidator
from jade_core.client import JadeClient

validator = JadeValidator()
client = JadeClient()

# Before executing any skill, validate it
skill = client.load_file("community_skill.json")
result = validator.validate_dict(skill.to_dict())

if not result.valid:
    raise SecurityError(f"Skill rejected: {result.errors}")

# Safe to execute
```

## 5-Layer Security Engine

### Layer 1: JSON Schema Validation

Validates structural integrity against the JADE Schema v1.0. Every skill must declare:
- `skill_id`, `metadata`, `trigger`, `input_schema`, `output_schema`
- `execution_dag` with typed nodes, edges, entry/exit points
- `security` block with explicit network whitelist and file permissions

### Layer 2: Code Injection Detection

Scans all string values for 22 executable patterns:

```
eval(  exec(  import  require(  __import__  subprocess
os.system  os.popen  child_process  Function(  setTimeout(
setInterval(  new Function  .call(  .apply(  .bind(
<script  javascript:  data:text/html  onclick=  onerror=  onload=
```

A single match → ❌ Rejected.

### Layer 3: Dangerous Command Blocking

Blocks 25+ system-level dangerous patterns:

```
rm -rf  mkfs  dd if=  chmod 777  :(){ :|:& };:
curl | sh  wget | sh  pip install --user  npm install -g
sudo  su -  /etc/passwd  /etc/shadow  ~/.ssh  .env
```

### Layer 4: Network & Data Leak Prevention

- Every network-accessing skill must declare `network_whitelist`
- Wildcard `*` triggers a warning
- Scans for potential data exfiltration patterns (API keys, tokens, credentials in URLs)

### Layer 5: DAG Integrity Verification

Validates the execution graph is a proper DAG:
- **Cycle detection** — no infinite loops possible
- **Reachability proof** — every node is reachable from `entry_node`
- **Exit completeness** — all paths terminate at declared `exit_node`
- **Action whitelist** — every node action must be in the 61 allowed atomic actions

## Formal Verification

JadeGate's security properties are not heuristic — they are mathematically provable.

### DAG Safety (Graph Theory)

A JADE skill's execution graph G = (V, E) must satisfy:

```
∀ v ∈ V : v is reachable from entry_node          (Reachability)
∀ path P in G : P terminates at some exit_node     (Termination)
¬∃ cycle C in G                                     (Acyclicity)
∀ v ∈ V : action(v) ∈ AllowedActions               (Action Safety)
```

Cycle detection uses DFS with three-color marking (O(V+E)):

```python
def has_cycle(graph):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {v: WHITE for v in graph}

    def dfs(u):
        color[u] = GRAY
        for v in graph[u]:
            if color[v] == GRAY:    # Back edge = cycle
                return True
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    return any(dfs(v) for v in graph if color[v] == WHITE)
```

### Bayesian Trust Scoring

Each skill's trust score is computed using Bayesian posterior updating:

```
P(safe | evidence) = P(evidence | safe) × P(safe) / P(evidence)
```

In practice, with success count s and failure count f:

```
confidence = (s + α) / (s + f + α + β)
```

Where α=1, β=1 (uniform prior). As a skill accumulates successful validations and executions, its confidence approaches 1.0. A single security violation drops it significantly.

```python
class BayesianScorer:
    def __init__(self, alpha=1.0, beta=1.0):
        self.alpha = alpha
        self.beta = beta

    def score(self, successes: int, failures: int) -> float:
        return (successes + self.alpha) / (successes + failures + self.alpha + self.beta)

    def update(self, success: bool, current_score: dict) -> dict:
        if success:
            current_score["successes"] += 1
        else:
            current_score["failures"] += 1
        current_score["confidence"] = self.score(
            current_score["successes"],
            current_score["failures"]
        )
        return current_score
```

### Non-Turing-Completeness Proof

JADE skills are provably non-Turing-complete because:

1. **No unbounded loops** — `loop_iterate` requires a finite, pre-declared collection
2. **No recursion** — DAG acyclicity prevents self-referencing execution paths
3. **No dynamic code generation** — all actions are statically declared in the schema
4. **No arbitrary memory access** — variable references use template syntax `{{node.output.field}}`

This means: **it is impossible to write a JADE skill that runs forever, consumes unbounded resources, or executes arbitrary code.**

## Skill Registry

35 verified skills across 8 categories:

| Category | Count | Examples |
|----------|-------|---------|
| 🌐 Web & Search | 6 | `web_search_query`, `webpage_screenshot`, `rss_feed_reader` |
| 📡 API Integration | 5 | `notion_page_read`, `github_create_issue`, `exa_semantic_search` |
| 🔧 System & DevOps | 6 | `git_clone_repo`, `docker_container_list`, `ssh_remote_exec` |
| 📁 File & Data | 4 | `file_batch_rename`, `csv_data_analysis`, `pdf_table_parser` |
| 🔒 Network & Security | 5 | `dns_lookup`, `ssl_cert_check`, `whois_lookup` |
| 💬 Messaging | 3 | `slack_send_message`, `discord_webhook_send`, `telegram_send_msg` |
| 🧠 AI & NLP | 3 | `text_translation`, `text_sentiment`, `webpage_content_extract` |
| 🛠️ Utilities | 3 | `timezone_query`, `qr_code_generate`, `base64_file_encode` |

## Atomic Actions

61 whitelisted operations organized by category:

| Category | Actions |
|----------|---------|
| HTTP | `http_get`, `http_post` |
| File | `file_read`, `file_write`, `file_list`, `file_delete`, `file_copy`, `file_move` |
| JSON | `json_parse`, `json_extract` |
| Text | `text_extract`, `text_split`, `text_join`, `text_replace`, `text_sanitize`, `text_template` |
| Browser | `page_navigate`, `page_click`, `page_type`, `page_extract`, `page_screenshot`, `page_wait` |
| AI/LLM | `llm_summarize`, `llm_classify`, `llm_extract` |
| System | `shell_exec`, `env_read` |
| Time | `time_now`, `time_convert`, `time_diff` |
| Messaging | `msg_send`, `msg_read` |
| Image | `image_resize`, `image_convert`, `qr_generate` |
| Encoding | `url_encode`, `url_decode`, `base64_encode`, `base64_decode`, `hash_compute` |
| Control | `condition_check`, `loop_iterate`, `delay`, `wait`, `error_handle`, `return_result`, `return_error`, `human_confirm` |

New actions can be proposed via PR. Each must include a risk assessment.

## Project Structure

```
jade-core/
├── jade_core/              # Core Python library
│   ├── validator.py        # 5-layer security validator
│   ├── security.py         # Zero-trust security engine
│   ├── dag.py              # DAG analyzer (cycle detection, reachability)
│   ├── client.py           # Client SDK
│   ├── registry.py         # Bayesian confidence registry
│   └── models.py           # Data models
├── jade_schema/            # JSON Schema v1.0 + allowed atomic actions
├── jade_skills/            # Official verified skills (💠)
├── converted_skills/       # Community verified skills (💠)
├── jade_registry/          # Skill index with trust scores
├── tests/                  # 135 test cases
├── .github/workflows/      # CI/CD (auto-publish to PyPI on release)
└── tools/                  # Skill converters and generators
```

## Roadmap

- [x] **v0.1** — Core validator, 35 skills, 61 atomic actions, PyPI + crates.io
- [ ] **v0.2** — CLI tools (`jade list`, `jade verify`, `jade search`, `jade install`)
- [ ] **v0.3** — Cryptographic signing (🔏 JADE Sealed) + contributor attestation
- [ ] **v0.4** — Global trust network with Bayesian routing + time-decay weights
- [ ] **v0.5** — Rust-native validator (target: <10ms per skill verification)
- [ ] **v1.0** — DAG execution engine + runtime sandboxing

## Contributing

Every submitted skill must pass all 5 validation layers:

```bash
jade verify your_skill.json
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

[MIT](./LICENSE)

---

<div align="center">

**💠 JadeGate** — *Pass the Gate. Trust the Jade.*

*春风不度玉门关*

[GitHub](https://github.com/JadeGate/jade-core) · [PyPI](https://pypi.org/project/jadegate/) · [crates.io](https://crates.io/crates/jadegate)

</div>
