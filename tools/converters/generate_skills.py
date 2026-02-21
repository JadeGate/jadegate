#!/usr/bin/env python3
"""
Project JADE - Batch Skill Generator
Generates 25+ real JADE skills based on actual MCP servers and OpenClaw capabilities.
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from jade_core.validator import JadeValidator

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def meta(name, desc, author, tags, license_str="MIT"):
    return {
        "name": name, "version": "1.0.0", "description": desc[:1024],
        "author": author, "tags": tags[:10], "license": license_str,
        "created_at": NOW, "updated_at": NOW,
    }

def trigger(task_types):
    if isinstance(task_types, str):
        return {"type": "task_intent", "conditions": [{"field": "task.type", "operator": "equals", "value": task_types}]}
    return {"type": "task_intent", "conditions": [{"field": "task.type", "operator": "in", "value": task_types}]}

def sec(net=None, fr=None, fw=None, sandbox="strict", timeout=30000):
    return {
        "network_whitelist": net or [], "file_permissions": {"read": fr or [], "write": fw or []},
        "max_execution_time_ms": timeout, "max_retries": 2,
        "sandbox_level": sandbox, "dangerous_patterns": [],
    }

def skill(sid, metadata, trig, inp, out, nodes, edges, entry, exits, security, mcp=True, caps=None):
    return {
        "jade_version": "1.0.0", "skill_id": sid, "metadata": metadata,
        "trigger": trig,
        "input_schema": {"required_params": inp},
        "output_schema": {"fields": out},
        "execution_dag": {"nodes": nodes, "edges": edges, "entry_node": entry, "exit_node": exits},
        "security": security,
        "mcp_compatible": mcp, "required_mcp_capabilities": caps or [],
    }

SKILLS = []
