"""
Shared test fixtures for Project JADE test suite.
"""

import json
import os
import tempfile
import shutil
import pytest
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
SKILLS_DIR = PROJECT_ROOT / "jade_skills"
SCHEMA_DIR = PROJECT_ROOT / "jade_schema"


def _make_minimal_skill(**overrides):
    """Create a minimal valid JADE skill dict for testing."""
    base = {
        "jade_version": "1.0.0",
        "skill_id": "test_skill",
        "metadata": {
            "name": "Test Skill",
            "version": "1.0.0",
            "description": "A test skill for unit testing",
            "author": "test-author",
            "tags": ["test"],
            "license": "MIT",
            "created_at": "2026-02-21T00:00:00Z",
            "updated_at": "2026-02-21T00:00:00Z",
        },
        "trigger": {
            "type": "manual",
            "conditions": [
                {"field": "task.type", "operator": "equals", "value": "test"}
            ],
        },
        "input_schema": {
            "required_params": [
                {"name": "input_text", "type": "string", "description": "Test input"}
            ]
        },
        "output_schema": {
            "fields": [
                {"name": "result", "type": "string", "description": "Test output"}
            ]
        },
        "execution_dag": {
            "nodes": [
                {
                    "id": "step_one",
                    "action": "json_parse",
                    "params": {"input": "{{input.input_text}}"},
                },
                {
                    "id": "step_two",
                    "action": "return_result",
                    "params": {"result": "{{step_one.output.data}}"},
                },
            ],
            "edges": [
                {"from": "step_one", "to": "step_two"}
            ],
            "entry_node": "step_one",
            "exit_node": ["step_two"],
        },
        "security": {
            "network_whitelist": [],
            "file_permissions": {"read": [], "write": []},
            "max_execution_time_ms": 10000,
            "max_retries": 0,
            "sandbox_level": "strict",
            "dangerous_patterns": [],
        },
        "mcp_compatible": True,
        "required_mcp_capabilities": [],
    }
    # Apply overrides via deep merge
    _deep_merge(base, overrides)
    return base


def _deep_merge(base, override):
    """Deep merge override into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


@pytest.fixture
def minimal_skill_dict():
    """A minimal valid JADE skill as a dict."""
    return _make_minimal_skill()


@pytest.fixture
def minimal_skill_file(tmp_path, minimal_skill_dict):
    """Write a minimal valid skill to a temp file and return the path."""
    path = tmp_path / "test_skill.json"
    path.write_text(json.dumps(minimal_skill_dict, indent=2), encoding="utf-8")
    return str(path)


@pytest.fixture
def all_skill_files():
    """Return paths to all 5 golden skills."""
    return sorted(str(p) for p in SKILLS_DIR.glob("*.json"))


@pytest.fixture
def weather_skill_dict():
    """Load the weather API skill as a dict."""
    path = SKILLS_DIR / "weather_api.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def email_skill_dict():
    """Load the email send skill as a dict."""
    path = SKILLS_DIR / "email_send_safe.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def validator():
    """Create a JadeValidator instance."""
    from jade_core.validator import JadeValidator
    return JadeValidator()


@pytest.fixture
def security_engine():
    """Create a SecurityEngine instance with default allowed actions."""
    from jade_core.security import SecurityEngine
    schema_file = SCHEMA_DIR / "allowed_atomic_actions.json"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    actions = []
    for cat in data.get("categories", {}).values():
        actions.extend(cat.get("actions", {}).keys())
    engine = SecurityEngine(allowed_actions=actions)
    return engine


@pytest.fixture
def dag_analyzer():
    """Create a DAGAnalyzer instance."""
    from jade_core.dag import DAGAnalyzer
    return DAGAnalyzer()


@pytest.fixture
def registry(tmp_path):
    """Create a JadeRegistry instance with a temp index file."""
    index_path = str(tmp_path / "index.json")
    from jade_core.registry import JadeRegistry
    return JadeRegistry(index_path=index_path)


@pytest.fixture
def client(tmp_path, validator, registry):
    """Create a JadeClient instance with temp cache."""
    from jade_core.client import JadeClient
    return JadeClient(
        cache_dir=str(tmp_path / "cache"),
        validator=validator,
        registry=registry,
    )


@pytest.fixture
def tmp_skills_dir(tmp_path):
    """Copy all golden skills to a temp directory."""
    dest = tmp_path / "skills"
    shutil.copytree(str(SKILLS_DIR), str(dest))
    return str(dest)


def make_skill(**overrides):
    """Public helper to create skill dicts in tests."""
    return _make_minimal_skill(**overrides)
