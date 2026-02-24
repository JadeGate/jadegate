"""
💠 JadeGate MCP Server
========================
Exposes JadeGate as a standard MCP server.

After `pip install jadegate`, add to your MCP config:

  Claude Desktop (~/.claude/claude_desktop_config.json):
    { "mcpServers": { "jadegate": { "command": "jade", "args": ["mcp-serve"] } } }

  Cursor (.cursor/mcp.json):
    { "mcpServers": { "jadegate": { "command": "jade", "args": ["mcp-serve"] } } }

  OpenClaw (config.yaml):
    mcp_servers:
      - name: jadegate
        command: jade mcp-serve

The LLM will then see jade_search, jade_verify, jade_info as available tools.
It will AUTOMATICALLY use them when it needs to find or verify skills.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def make_tools():
    """Define MCP tools that the LLM can call."""
    return [
        {
            "name": "jade_search",
            "description": "Search 1819 verified AI agent skills by keyword. Returns matching skills with trust seals (💠 Root / 🔹 Community). Use this when you need to find a tool or integration.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What you're looking for, e.g. 'send slack message' or 'github issues'"},
                    "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10}
                },
                "required": ["query"]
            }
        },
        {
            "name": "jade_list",
            "description": "List all 1819 verified skills in the JadeGate registry. Filter by type (mcp/tool) or tag.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["mcp", "tool", "all"], "default": "all"},
                    "tag": {"type": "string", "description": "Filter by tag"}
                }
            }
        },
        {
            "name": "jade_info",
            "description": "Get detailed info about a specific skill: description, security policy, trust seal, DAG structure.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skill_id": {"type": "string", "description": "Skill ID, e.g. 'mcp_github_create_issue'"}
                },
                "required": ["skill_id"]
            }
        },
        {
            "name": "jade_verify",
            "description": "Run 5-layer deterministic verification on a skill JSON. Checks schema, DAG, security, injection, and cryptographic signature.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skill_json": {"type": "string", "description": "Skill JSON content or file path"}
                },
                "required": ["skill_json"]
            }
        },
        {
            "name": "jade_compose",
            "description": "Given a complex task description, suggest a chain of skills to accomplish it. Uses the skill graph to find optimal combinations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "What you want to accomplish, e.g. 'monitor github PRs and notify slack'"}
                },
                "required": ["task"]
            }
        },
        {
            "name": "jade_doctor",
            "description": "Scan the current environment (API keys, project files) and recommend which JadeGate skills are ready to use.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]


def handle_tool_call(name: str, arguments: dict) -> str:
    """Execute a tool call and return result."""
    from jade_core.graph import SkillGraph
    from jade_core.validator import JadeValidator
    from jade_core.autodiscovery import JadeAutoDiscovery

    base = _find_base()
    
    if name == "jade_search":
        g = SkillGraph()
        g.load_from_directory(
            os.path.join(base, 'jade_skills/mcp'),
            os.path.join(base, 'jade_skills/tools')
        )
        results = g.search(arguments["query"], limit=arguments.get("limit", 10))
        return json.dumps(results, indent=2)

    elif name == "jade_list":
        g = SkillGraph()
        g.load_from_directory(
            os.path.join(base, 'jade_skills/mcp'),
            os.path.join(base, 'jade_skills/tools')
        )
        skills = []
        for node in sorted(g.nodes.values(), key=lambda n: n.skill_id):
            if arguments.get("type", "all") != "all":
                if arguments["type"] == "mcp" and node.skill_type != "MCP":
                    continue
                if arguments["type"] == "tool" and node.skill_type != "Tool":
                    continue
            if arguments.get("tag") and arguments["tag"] not in node.tags:
                continue
            seal = "💠" if node.seal == "root" else "🔹" if node.seal in ("community", "partial") else "⬜"
            skills.append(f"{seal} {node.skill_id}: {node.description}")
        return "\n".join(skills)

    elif name == "jade_info":
        sid = arguments["skill_id"]
        for d in ['jade_skills/mcp', 'jade_skills/tools']:
            path = os.path.join(base, d, f"{sid}.json")
            if os.path.exists(path):
                with open(path) as f:
                    skill = json.load(f)
                return json.dumps({
                    "skill_id": skill["skill_id"],
                    "name": skill["metadata"]["name"],
                    "description": skill["metadata"]["description"],
                    "tags": skill["metadata"].get("tags", []),
                    "security": skill["security"],
                    "sealed": bool(skill.get("jade_signature")),
                    "dag_nodes": len(skill["execution_dag"]["nodes"]),
                }, indent=2)
        return json.dumps({"error": f"Skill '{sid}' not found"})

    elif name == "jade_verify":
        v = JadeValidator()
        skill_input = arguments["skill_json"]
        if os.path.exists(skill_input):
            result = v.validate_file(skill_input)
        else:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(skill_input)
                tmp = f.name
            result = v.validate_file(tmp)
            os.unlink(tmp)
        return json.dumps({
            "valid": result.valid,
            "issues": [{"severity": i.severity.value, "code": i.code, "message": i.message} for i in result.issues]
        }, indent=2)

    elif name == "jade_compose":
        g = SkillGraph()
        g.load_from_directory(
            os.path.join(base, 'jade_skills/mcp'),
            os.path.join(base, 'jade_skills/tools')
        )
        result = g.compose(arguments["task"])
        return json.dumps(result, indent=2, default=str)

    elif name == "jade_doctor":
        disco = JadeAutoDiscovery()
        report = disco.doctor()
        return json.dumps(report, indent=2, default=str)

    return json.dumps({"error": f"Unknown tool: {name}"})


def _find_base():
    """Find JadeGate base directory."""
    import platform
    candidates = [
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.path.expanduser("~/.jadegate"),
        os.path.join(os.environ.get("APPDATA", ""), "jadegate") if platform.system() == "Windows" else "",
    ]
    for c in candidates:
        if not c:
            continue
        if os.path.isdir(os.path.join(c, "jade_skills")):
            return c
        if os.path.isdir(os.path.join(c, "skills", "mcp")):
            return c
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_mcp_server():
    """
    Run as MCP stdio server.
    Speaks JSON-RPC 2.0 over stdin/stdout (MCP protocol).
    """
    tools = make_tools()

    def send(msg):
        out = json.dumps(msg)
        sys.stdout.write(f"Content-Length: {len(out)}\r\n\r\n{out}")
        sys.stdout.flush()

    def read_message():
        headers = {}
        while True:
            line = sys.stdin.readline()
            if not line or line.strip() == "":
                break
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()
        length = int(headers.get("Content-Length", 0))
        if length:
            body = sys.stdin.read(length)
            return json.loads(body)
        return None

    # Server info
    server_info = {
        "name": "jadegate",
        "version": "1.0.0",
        "description": "💠 JadeGate — 1819 verified AI agent skills with deterministic security",
    }

    while True:
        try:
            msg = read_message()
            if not msg:
                break

            method = msg.get("method", "")
            msg_id = msg.get("id")

            if method == "initialize":
                send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": server_info,
                    }
                })

            elif method == "notifications/initialized":
                pass  # no response needed

            elif method == "tools/list":
                send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": tools}
                })

            elif method == "tools/call":
                params = msg.get("params", {})
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                try:
                    result_text = handle_tool_call(tool_name, tool_args)
                    send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": result_text}]
                        }
                    })
                except Exception as e:
                    send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Error: {e}"}],
                            "isError": True
                        }
                    })

            elif method == "ping":
                send({"jsonrpc": "2.0", "id": msg_id, "result": {}})

            else:
                if msg_id:
                    send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"}
                    })

        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            sys.stderr.write(f"JadeGate MCP error: {e}\n")


if __name__ == "__main__":
    run_mcp_server()
