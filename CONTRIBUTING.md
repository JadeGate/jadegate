# Contributing to JadeGate

## Submit a Skill

### 1. Create your skill JSON

```json
{
  "jade_version": "1.0.0",
  "skill_id": "my_awesome_tool",
  "metadata": {
    "name": "My Awesome Tool",
    "version": "1.0.0",
    "description": "What it does",
    "author": "your-name",
    "tags": ["mcp", "tool"],
    "license": "MIT"
  },
  "trigger": {
    "type": "task_intent",
    "conditions": [{"field": "task.type", "operator": "in", "value": ["my_awesome_tool"]}]
  },
  "input_schema": {
    "required_params": [{"name": "input", "type": "string", "description": "Input data"}],
    "optional_params": []
  },
  "output_schema": {
    "fields": [{"name": "result", "type": "object", "description": "Output"}]
  },
  "execution_dag": {
    "nodes": [
      {"id": "fetch", "action": "http_get", "params": {"endpoint": "/api"}},
      {"id": "ret", "action": "return_result", "params": {}}
    ],
    "edges": [{"from": "fetch", "to": "ret"}],
    "entry_node": "fetch",
    "exit_node": "ret"
  },
  "security": {
    "network_whitelist": ["api.example.com"],
    "file_permissions": {"read": [], "write": []},
    "max_execution_time_ms": 30000,
    "max_retries": 2,
    "sandbox_level": "strict",
    "dangerous_patterns": []
  }
}
```

### 2. Verify locally

```bash
pip install jadegate
jade verify my_skill.json
```

All 5 layers must pass:
- ✅ Layer 1: JSON Schema (structural integrity)
- ✅ Layer 2: Code Injection Scan (22 patterns)
- ✅ Layer 3: Dangerous Commands (25 patterns)
- ✅ Layer 4: Network & Data Leak (whitelist enforcement)
- ✅ Layer 5: DAG Integrity (acyclicity, reachability)

### 3. Submit a PR

Place your skill in:
- `jade_skills/mcp/` — for MCP server wrappers
- `jade_skills/tools/` — for general tools

CI will automatically run 5-layer verification and sign on merge.

### For Agents

Agents can verify skills programmatically:

```python
from jade_core.validator import JadeValidator

v = JadeValidator()
result = v.validate_file("skill.json")
print(result.valid)  # True/False
```

Or via the MCP server:

```bash
npx @jadegate/mcp-server
```

Then call `verify_skill` with the skill JSON.

## Report a Security Issue

Email: security@jadegate.io

Do NOT open a public issue for security vulnerabilities.

## Code Style

- Python: follow existing patterns, no external dependencies in core
- JSON skills: run `jade verify` before submitting
- Tests: add test cases for new detection patterns

## License

By contributing, you agree that your contributions will be licensed under BSL 1.1.
