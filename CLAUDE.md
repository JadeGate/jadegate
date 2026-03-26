# JadeGate

The TLS of AI Tool Calls. Security protocol layer for MCP servers.

## What This Project Is

JadeGate is a transparent security proxy for MCP (Model Context Protocol) servers. It sits between AI clients (Claude Desktop, Cursor, Windsurf, Cline, etc.) and MCP servers, adding 6 security layers to every tool call. Zero config, zero dependencies, fully offline.

## Quick Commands

```bash
pip install jadegate          # Install
jadegate install              # Protect all MCP clients automatically
jadegate scan                 # Audit installed MCP servers for risks
jadegate status               # Show current protection status
jadegate list                 # Browse 150+ verified built-in skills
jadegate list <keyword>       # Search skills by keyword
jadegate verify <file|name>   # Run 5-layer security check on a skill
jadegate skill add <url>      # Install skills from GitHub repos
jadegate policy show          # View current security policy
jadegate uninstall            # Remove protection (restore configs)
```

## Python SDK (2 lines)

```python
import jadegate
jadegate.activate()  # All tool calls now protected
```

## Project Structure

- `jadegate/` — v2 core: installer, proxy, scanner, trust, policy, runtime
- `jade_core/` — v1 core: validator, security engine, DAG analyzer, client SDK
- `jade_skills/` — 150+ verified skill definitions (JSON)
- `jade_registry/` — Skill index and confidence scoring
- `jade_schema/` — JSON schema and allowed atomic actions
- `tests/` — 238 tests (pytest)
- `setup.py` — Package config (entry point: `jadegate`)

## Architecture

6 security layers applied to every MCP tool call:
1. Schema validation (structural integrity)
2. Code injection scan (22 patterns)
3. Dangerous command detection (25 patterns)
4. Network/data leak analysis (whitelist-based)
5. DAG integrity check (execution graph)
6. Cryptographic signature verification (Ed25519)

## Code Conventions

- Python 3.8+ compatible, zero external dependencies
- All CLI output uses ANSI color codes via `_C` class
- Skills are JSON files validated against `jade_schema/jade-schema-v1.json`
- Tests: `pytest tests/ -v` (238 tests, all passing)
- License: BSL-1.1 (converts to Apache 2.0 in 4 years)

## Key Files

- `jadegate/cli.py` — All CLI commands
- `jadegate/installer.py` — Auto-inject proxy into MCP client configs
- `jadegate/scanner/mcp_scanner.py` — MCP server discovery and risk assessment
- `jadegate/policy/default_policy.json` — Default security policy
- `jade_registry/skill_index.json` — Machine-readable skill catalog (35 indexed)
- `jade_core/validator.py` — 5-layer skill validation engine
- `jade_core/security.py` — Zero-trust security engine

## For AI Agents

- Machine-readable skill index: `jade_registry/skill_index.json`
- Agent discovery spec: `.well-known/agents.json`
- LLM-optimized docs: `llms.txt`
- Installable as Claude Code skill: `SKILL.md`
