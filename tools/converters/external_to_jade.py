#!/usr/bin/env python3
"""
Project JADE - External Skill Converter
Converts MCP servers, OpenClaw skills, and other formats to JADE JSON.

Usage:
    python3 external_to_jade.py --type mcp --name "notion" --output converted_skills/
    python3 external_to_jade.py --type openclaw --name "github" --output converted_skills/
    python3 external_to_jade.py --batch templates/batch_definitions.json --output converted_skills/
"""

import json
import hashlib
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from jade_core.validator import JadeValidator


def make_skill_id(name: str) -> str:
    """Convert a name to a valid JADE skill_id (lowercase, underscores, 3-64 chars)."""
    sid = name.lower().replace("-", "_").replace(" ", "_").replace(".", "_")
    sid = "".join(c for c in sid if c.isalnum() or c == "_")
    if not sid or not sid[0].isalpha():
        sid = "skill_" + sid
    return sid[:64]


def build_jade_skill(
    skill_id: str,
    name: str,
    description: str,
    author: str,
    tags: List[str],
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    entry_node: str,
    exit_nodes: List[str],
    network_whitelist: List[str] = None,
    file_read: List[str] = None,
    file_write: List[str] = None,
    sandbox_level: str = "strict",
    trigger_type: str = "task_intent",
    trigger_conditions: List[Dict] = None,
    input_params: List[Dict] = None,
    output_fields: List[Dict] = None,
    mcp_compatible: bool = True,
    mcp_capabilities: List[str] = None,
    max_execution_time_ms: int = 30000,
    source_url: str = "",
    license_str: str = "MIT",
) -> Dict[str, Any]:
    """Build a complete JADE skill dictionary."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if trigger_conditions is None:
        trigger_conditions = [{"field": "task.type", "operator": "equals", "value": skill_id}]
    if input_params is None:
        input_params = [{"name": "query", "type": "string", "description": "Input query"}]
    if output_fields is None:
        output_fields = [{"name": "result", "type": "string", "description": "Operation result"}]
    if tags and len(tags) > 10:
        tags = tags[:10]

    desc = description[:1024] if description else name

    skill = {
        "jade_version": "1.0.0",
        "skill_id": skill_id,
        "metadata": {
            "name": name,
            "version": "1.0.0",
            "description": desc,
            "author": author,
            "tags": tags[:10],
            "license": license_str,
            "created_at": now,
            "updated_at": now,
        },
        "trigger": {
            "type": trigger_type,
            "conditions": trigger_conditions,
        },
        "input_schema": {
            "required_params": input_params,
        },
        "output_schema": {
            "fields": output_fields,
        },
        "execution_dag": {
            "nodes": nodes,
            "edges": edges,
            "entry_node": entry_node,
            "exit_node": exit_nodes,
        },
        "security": {
            "network_whitelist": network_whitelist or [],
            "file_permissions": {
                "read": file_read or [],
                "write": file_write or [],
            },
            "max_execution_time_ms": max_execution_time_ms,
            "max_retries": 2,
            "sandbox_level": sandbox_level,
            "dangerous_patterns": [],
        },
        "mcp_compatible": mcp_compatible,
        "required_mcp_capabilities": mcp_capabilities or [],
    }

    if source_url:
        skill["metadata"]["source_url"] = source_url

    return skill


def validate_and_save(skill: Dict[str, Any], output_dir: str, validator: JadeValidator) -> bool:
    """Validate a skill and save it if valid."""
    result = validator.validate_dict(skill)
    sid = skill.get("skill_id", "unknown")
    if result.valid:
        out_path = Path(output_dir) / f"{sid}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(skill, f, indent=2, ensure_ascii=False)
        print(f"  💠 VERIFIED & SAVED: {out_path}")
        return True
    else:
        print(f"  🌫️ REJECTED: {sid}")
        for issue in result.errors:
            print(f"     [{issue.code}] {issue.message}")
        for issue in result.warnings:
            print(f"     ⚠️ {issue.code}: {issue.message}")
        return False


def convert_batch(definitions: List[Dict[str, Any]], output_dir: str) -> Dict[str, int]:
    """Convert a batch of skill definitions to JADE format."""
    validator = JadeValidator()
    stats = {"total": 0, "passed": 0, "failed": 0}

    for defn in definitions:
        stats["total"] += 1
        skill = build_jade_skill(**defn)
        if validate_and_save(skill, output_dir, validator):
            stats["passed"] += 1
        else:
            stats["failed"] += 1

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JADE External Skill Converter")
    parser.add_argument("--batch", type=str, help="Path to batch definitions JSON")
    parser.add_argument("--output", type=str, default="converted_skills", help="Output directory")
    parser.add_argument("--validate-only", type=str, help="Validate an existing JADE skill file")
    args = parser.parse_args()

    if args.validate_only:
        v = JadeValidator()
        r = v.validate_file(args.validate_only)
        status = "💠 VERIFIED" if r.valid else "🌫️ REJECTED"
        print(f"{status}: {args.validate_only}")
        if not r.valid:
            for i in r.errors:
                print(f"  [{i.code}] {i.message}")
        sys.exit(0 if r.valid else 1)

    if args.batch:
        with open(args.batch, "r") as f:
            defs = json.load(f)
        stats = convert_batch(defs, args.output)
        print(f"\n{'='*60}")
        print(f"💠 JADE Batch Conversion Complete")
        print(f"   Total: {stats['total']} | Passed: {stats['passed']} | Failed: {stats['failed']}")
        print(f"{'='*60}")
    else:
        print("Usage: python3 external_to_jade.py --batch <definitions.json> --output <dir>")
        print("       python3 external_to_jade.py --validate-only <skill.json>")
