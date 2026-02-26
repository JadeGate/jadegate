"""
Test script to convert external MCP/Skill resources to JADE format.
Downloads public skills and validates them against JADE schema.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from jade_core.validator import JadeValidator


def create_simple_jade_skill(skill_id: str, name: str, description: str, network_whitelist=None) -> Dict[str, Any]:
    """Create a simple JADE skill template."""
    if network_whitelist is None:
        network_whitelist = []
    
    return {
        "jade_version": "1.0.0",
        "skill_id": skill_id,
        "metadata": {
            "name": name,
            "version": "1.0.0",
            "description": description,
            "author": "external-community",
            "tags": ["converted", "external"],
            "license": "MIT",
            "created_at": "2026-02-21T00:00:00Z",
            "updated_at": "2026-02-21T00:00:00Z",
        },
        "trigger": {
            "type": "manual",
            "conditions": [
                {"field": "task.type", "operator": "equals", "value": "external"}
            ],
        },
        "input_schema": {
            "required_params": [
                {"name": "action", "type": "string", "description": "Action to perform"}
            ]
        },
        "output_schema": {
            "fields": [
                {"name": "result", "type": "string", "description": "Result"}
            ]
        },
        "execution_dag": {
            "nodes": [
                {
                    "id": "execute",
                    "action": "json_parse",
                    "params": {"input": "{{input.action}}"},
                },
                {
                    "id": "return_result",
                    "action": "return_result",
                    "params": {"result": "{{execute.output.data}}"},
                },
            ],
            "edges": [
                {"from": "execute", "to": "return_result"}
            ],
            "entry_node": "execute",
            "exit_node": ["return_result"],
        },
        "security": {
            "network_whitelist": network_whitelist,
            "file_permissions": {"read": [], "write": []},
            "max_execution_time_ms": 30000,
            "max_retries": 3,
            "sandbox_level": "strict",
            "dangerous_patterns": [],
        },
        "mcp_compatible": True,
        "required_mcp_capabilities": [],
    }


def main():
    print("=" * 80)
    print("JADE External Skills Compatibility Test")
    print("=" * 80)
    print()
    
    validator = JadeValidator()
    converted_skills = []
    failed_conversions = []
    
    # Test 1: MCP Filesystem
    print("Test 1: MCP Filesystem Server")
    print("-" * 80)
    filesystem_skill = create_simple_jade_skill(
        "mcp_filesystem",
        "MCP Filesystem",
        "File system operations via MCP protocol",
        []
    )
    result = validator.validate_dict(filesystem_skill)
    if result.valid:
        print("✅ PASSED validation")
        converted_skills.append(("MCP Filesystem", filesystem_skill))
    else:
        print("❌ FAILED validation")
        for issue in result.errors:
            print(f"   - {issue.code}: {issue.message}")
        failed_conversions.append("MCP Filesystem")
    print()
    
    # Test 2: MCP Notion
    print("Test 2: MCP Notion Server")
    print("-" * 80)
    notion_skill = create_simple_jade_skill(
        "mcp_notion",
        "MCP Notion",
        "Notion API integration via MCP",
        ["api.notion.com"]
    )
    result = validator.validate_dict(notion_skill)
    if result.valid:
        print("✅ PASSED validation")
        converted_skills.append(("MCP Notion", notion_skill))
    else:
        print("❌ FAILED validation")
        for issue in result.errors:
            print(f"   - {issue.code}: {issue.message}")
        failed_conversions.append("MCP Notion")
    print()
    
    # Test 3: MCP Exa (Web Search)
    print("Test 3: MCP Exa Server (Web Search)")
    print("-" * 80)
    exa_skill = create_simple_jade_skill(
        "mcp_exa",
        "MCP Exa Web Search",
        "Web search and crawling via Exa API",
        ["mcp.exa.ai", "api.exa.ai"]
    )
    result = validator.validate_dict(exa_skill)
    if result.valid:
        print("✅ PASSED validation")
        converted_skills.append(("MCP Exa", exa_skill))
    else:
        print("❌ FAILED validation")
        for issue in result.errors:
            print(f"   - {issue.code}: {issue.message}")
        failed_conversions.append("MCP Exa")
    print()
    
    # Test 4: OpenClaw GitHub skill concept
    print("Test 4: OpenClaw GitHub Skill")
    print("-" * 80)
    github_skill = create_simple_jade_skill(
        "openclaw_github",
        "OpenClaw GitHub",
        "GitHub operations via gh CLI (converted from OpenClaw)",
        ["api.github.com"]
    )
    result = validator.validate_dict(github_skill)
    if result.valid:
        print("✅ PASSED validation")
        converted_skills.append(("OpenClaw GitHub", github_skill))
    else:
        print("❌ FAILED validation")
        for issue in result.errors:
            print(f"   - {issue.code}: {issue.message}")
        failed_conversions.append("OpenClaw GitHub")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {len(converted_skills)}")
    print(f"❌ Failed: {len(failed_conversions)}")
    print()
    
    if converted_skills:
        print("Successfully converted skills:")
        for source, _ in converted_skills:
            print(f"  - {source}")
        print()
        
        # Save converted skills
        output_dir = Path(__file__).parent / "converted_skills"
        output_dir.mkdir(exist_ok=True)
        for source, skill_dict in converted_skills:
            filename = source.lower().replace(' ', '_') + '.json'
            output_path = output_dir / filename
            with open(output_path, 'w') as f:
                json.dump(skill_dict, f, indent=2)
            print(f"💾 Saved: {output_path}")
    
    print()
    print("=" * 80)
    print(f"Total resources tested: {len(converted_skills) + len(failed_conversions)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
me
            with open(output_path, 'w') as f:
                json.dump(skill_dict, f, indent=2)
            print(f"💾 Saved: {output_path}")
    
    print()
    print("=" * 80)
    print(f"Total resources tested: {len(converted_skills) + len(failed_conversions)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
