# Project JADE 🟢

**Deterministic Security Protocol for AI Agents**

*The Package Manager and Immunity Network for AI Agent Skills.*

---

## What is JADE?

JADE (JSON-based Agent Deterministic Execution) is a structural security protocol that makes AI agent skills **safe by design, not by review**.

The core insight: if a skill definition is **non-Turing-complete** (pure JSON, no executable code), then security becomes a **structural property** rather than a behavioral one. You don't need to "test" if a skill is safe — you can **prove** it.

```
Traditional approach:  Code → Run → Hope it's safe → Review → Maybe safe
JADE approach:         JSON Schema → Validate → Mathematically safe → Execute
```

## Architecture: The JADE Trinity

### 1. The Schema (`jade_schema/`) — "The Constitution"

A strict JSON Schema that defines how skills must be structured:
- **Declarative only**: Skills describe WHAT to do, never HOW
- **No executable code**: Zero Turing-complete constructs allowed
- **Atomic actions**: Every operation must come from the allowed actions list
- **Explicit permissions**: Network whitelist, file permissions, sandbox level

### 2. The Validator (`jade_core/validator.py`) — "The Supreme Court"

A multi-layer validation engine:
- **Schema compliance**: Structural correctness check
- **Security scan**: Executable code detection, dangerous pattern matching, data exfiltration prevention
- **DAG analysis**: Cycle detection, reachability verification, orphan node detection
- **Semantic validation**: Cross-field consistency checks

### 3. The Registry (`jade_registry/`) — "The Index"

A Bayesian confidence-scored skill registry:
- **Hash-based indexing**: Every skill identified by its SHA-256 hash
- **Bayesian scoring**: Confidence updated via Beta distribution posterior
- **Time decay**: Unused skills lose confidence over time
- **Attestation system**: Agents report success/failure, feeding the scoring engine

## Quick Start

```python
from jade_core import JadeValidator, JadeClient, JadeRegistry

# Validate a skill
validator = JadeValidator()
result = validator.validate_file("jade_skills/weather_api.json")
print(f"Valid: {result.valid}")  # True

# Load and use skills
client = JadeClient()
skill, result = client.load_file("jade_skills/weather_api.json")
print(f"Skill: {skill.metadata.name}")  # Weather API Query SOP
print(f"Nodes: {len(skill.execution_dag.nodes)}")  # 10

# Register and track confidence
registry = JadeRegistry()
entry = registry.register(skill)
print(f"Confidence: {entry.confidence_score}")  # 0.5 (initial)

# Load all skills from a directory
results = client.load_directory("jade_skills/")
print(f"Loaded: {len(results)} skills")  # 5
```

## Golden Skills (v1.0)

| Skill | Description | Network | Sandbox |
|-------|-------------|---------|---------|
| `web_anti_crawl` | Anti-crawl bypass with robots.txt respect | `*` | strict |
| `pdf_table_parser` | PDF table extraction, no script execution | none | strict |
| `weather_api` | Free weather API with provider fallback | `wttr.in`, `api.open-meteo.com` | strict |
| `file_batch_rename` | Regex batch rename with collision detection | none | strict |
| `email_send_safe` | SMTP email with human confirmation gate | SMTP host | strict |

## Security Model

JADE enforces security at **five layers**:

1. **Non-Turing-Complete**: No `eval`, `exec`, `import`, `<script>`, `Function()` — 20+ patterns blocked
2. **Dangerous Command Detection**: `rm -rf`, `mkfs`, `sudo`, `curl|sh` — 25+ patterns blocked
3. **Network Whitelist**: Every domain must be explicitly declared; private IPs, `.onion`, `localhost` flagged
4. **Data Exfiltration Prevention**: Detects references to `~/.ssh/`, `.env`, `api_key`, `password`, `~/.aws/credentials`
5. **DAG Structural Safety**: Cycle detection, reachability proof, orphan node detection

## Bayesian Confidence Scoring

Skills earn trust through usage attestations:

```
P(reliable) = (successes + 1) / (successes + failures + 2)
```

- New skill: `0.5` (maximum uncertainty)
- 10 successes, 0 failures: `0.917`
- 100 successes, 1 failure: `0.990`
- 0 successes, 10 failures: `0.083`

Confidence decays exponentially without new attestations (half-life: 30 days).

## CI/CD Integration

JADE includes a GitHub Actions workflow that automatically:
1. Validates any skill JSON submitted via PR
2. Runs deep security scan
3. Comments verification results on the PR
4. Labels verified PRs with `✅ jade-verified`

## Project Structure

```
ProjectJADE/
├── jade_schema/                  # The "Constitution"
│   ├── jade-schema-v1.json       # Core schema definition
│   └── allowed_atomic_actions.json  # Periodic table of actions
├── jade_skills/                  # The "Sanctuary" - 5 golden skills
├── jade_core/                    # Core Python package
│   ├── validator.py              # Schema + security validator
│   ├── security.py               # Zero-trust security engine
│   ├── dag.py                    # DAG structural analyzer
│   ├── client.py                 # Agent-facing SDK
│   ├── registry.py               # Bayesian confidence registry
│   └── models.py                 # Data models
├── jade_registry/                # Global skill index
├── tests/                        # 135 tests, 100% pass
└── .github/workflows/            # CI/CD automation
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Philosophy

> Skills should be like laws — written in plain language, publicly auditable, and structurally incapable of harm.

JADE doesn't review code for safety. JADE makes unsafe code **structurally impossible**.

---

**License**: MIT
