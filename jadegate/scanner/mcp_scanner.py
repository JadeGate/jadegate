"""
JadeGate MCP Scanner — Discover and assess installed MCP servers.

Scans Claude Desktop, Cursor, and other known MCP client configs
to find installed MCP servers, then assesses their security posture.

All local. No network calls.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..trust.certificate import RiskProfile

logger = logging.getLogger("jadegate.scanner.mcp_scanner")


@dataclass
class MCPServerInfo:
    """Information about a discovered MCP server."""
    name: str
    command: List[str] = field(default_factory=list)
    source: str = ""  # "claude_desktop", "cursor", "custom"
    env: Dict[str, str] = field(default_factory=dict)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    risk_profile: Optional[RiskProfile] = None
    scan_error: str = ""
    scan_time_ms: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "source": self.source,
            "tools_count": len(self.tools),
            "tools": [{"name": t.get("name", "?"), "description": t.get("description", "")} for t in self.tools],
            "risk_profile": self.risk_profile.to_dict() if self.risk_profile else None,
            "scan_error": self.scan_error,
            "scan_time_ms": self.scan_time_ms,
        }


def _find_claude_desktop_config() -> Optional[str]:
    """Find Claude Desktop MCP config file."""
    system = platform.system()
    candidates = []
    if system == "Darwin":
        candidates.append(os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json"))
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(os.path.join(appdata, "Claude", "claude_desktop_config.json"))
    else:
        candidates.append(os.path.expanduser("~/.config/claude/claude_desktop_config.json"))
        candidates.append(os.path.expanduser("~/.config/Claude/claude_desktop_config.json"))
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _find_cursor_config() -> Optional[str]:
    """Find Cursor MCP config file."""
    system = platform.system()
    candidates = []
    if system == "Darwin":
        candidates.append(os.path.expanduser("~/Library/Application Support/Cursor/mcp.json"))
        candidates.append(os.path.expanduser("~/.cursor/mcp.json"))
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(os.path.join(appdata, "Cursor", "mcp.json"))
        candidates.append(os.path.expanduser("~/.cursor/mcp.json"))
    else:
        candidates.append(os.path.expanduser("~/.cursor/mcp.json"))
        candidates.append(os.path.expanduser("~/.config/cursor/mcp.json"))
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _parse_mcp_config(path: str, source: str) -> List[MCPServerInfo]:
    """Parse an MCP config file and extract server definitions."""
    servers = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        mcp_servers = data.get("mcpServers", {})
        for name, config in mcp_servers.items():
            cmd = config.get("command", "")
            args = config.get("args", [])
            env = config.get("env", {})
            if isinstance(cmd, str):
                command = [cmd] + (args if isinstance(args, list) else [])
            else:
                command = list(cmd) if cmd else []
            servers.append(MCPServerInfo(
                name=name, command=command, source=source, env=env,
            ))
    except Exception as e:
        logger.warning("Failed to parse %s: %s", path, e)
    return servers


def _assess_command_risk(cmd_str: str, tools: List[Dict] = None) -> RiskProfile:
    """Assess risk from command string and tool list."""
    text = cmd_str.lower()
    if tools:
        for t in tools:
            text += f" {t.get('name', '')} {t.get('description', '')}".lower()

    caps = []
    net = file_acc = shell = exfil = False

    if any(kw in text for kw in ("http", "fetch", "request", "url", "api", "webhook", "curl", "network")):
        net = True
        caps.append("network")
    if any(kw in text for kw in ("file", "read", "write", "path", "directory", "folder", "filesystem", "fs")):
        file_acc = True
        caps.append("filesystem")
    if any(kw in text for kw in ("exec", "shell", "command", "run", "bash", "terminal", "subprocess")):
        shell = True
        caps.append("shell")
    if any(kw in text for kw in ("send", "email", "post", "upload", "push", "deploy")):
        exfil = True
        caps.append("data_send")
    if any(kw in text for kw in ("search", "query", "list", "get", "browse")):
        caps.append("read_only")
    if any(kw in text for kw in ("puppeteer", "playwright", "browser", "selenium")):
        shell = True
        net = True
        caps.extend(["browser", "shell", "network"])

    if shell:
        level = "critical"
    elif net and file_acc:
        level = "high"
    elif net or exfil:
        level = "medium"
    elif file_acc:
        level = "medium"
    else:
        level = "low"

    return RiskProfile(
        level=level, capabilities=list(set(caps)),
        network_access=net, file_access=file_acc,
        shell_access=shell, data_exfil_risk=exfil,
    )


class MCPScanner:
    """
    Scans the system for installed MCP servers and assesses their security.
    """

    def __init__(self, extra_configs: Optional[List[str]] = None):
        self._extra_configs = extra_configs or []

    def discover(self) -> List[MCPServerInfo]:
        """Discover all MCP servers from known config locations."""
        servers: List[MCPServerInfo] = []

        claude_config = _find_claude_desktop_config()
        if claude_config:
            logger.info("Found Claude Desktop config: %s", claude_config)
            servers.extend(_parse_mcp_config(claude_config, "claude_desktop"))

        cursor_config = _find_cursor_config()
        if cursor_config:
            logger.info("Found Cursor config: %s", cursor_config)
            servers.extend(_parse_mcp_config(cursor_config, "cursor"))

        for path in self._extra_configs:
            if os.path.exists(path):
                servers.extend(_parse_mcp_config(path, "custom"))

        logger.info("Discovered %d MCP servers", len(servers))
        return servers

    def assess_server(self, server: MCPServerInfo, probe: bool = False) -> MCPServerInfo:
        """Assess a single MCP server's security posture."""
        start = time.time()

        if probe:
            server = self._probe_server(server)

        cmd_str = " ".join(server.command)
        server.risk_profile = _assess_command_risk(cmd_str, server.tools)
        server.scan_time_ms = (time.time() - start) * 1000
        return server

    def assess_all(self, servers: List[MCPServerInfo], probe: bool = False) -> List[MCPServerInfo]:
        """Assess all servers."""
        return [self.assess_server(s, probe=probe) for s in servers]

    def _probe_server(self, server: MCPServerInfo) -> MCPServerInfo:
        """Actually launch the server and get tools/list (optional, requires execution)."""
        if not server.command:
            server.scan_error = "No command specified"
            return server

        try:
            init_msg = json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05",
                           "capabilities": {}, "clientInfo": {"name": "jadegate-scanner", "version": "2.0.0"}},
            }) + "\n"
            list_msg = json.dumps({
                "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
            }) + "\n"

            proc = subprocess.Popen(
                server.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env={**os.environ, **server.env},
            )
            stdout, _ = proc.communicate(
                input=(init_msg + list_msg).encode(), timeout=10,
            )

            for line in stdout.decode(errors="replace").strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get("id") == 2 and "result" in msg:
                        server.tools = msg["result"].get("tools", [])
                except (json.JSONDecodeError, KeyError):
                    continue

        except subprocess.TimeoutExpired:
            server.scan_error = "Timeout (10s)"
            try:
                proc.kill()
            except Exception:
                pass
        except FileNotFoundError:
            server.scan_error = f"Command not found: {server.command[0]}"
        except Exception as e:
            server.scan_error = str(e)

        return server
