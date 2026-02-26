"""
JadeGate Installer — Auto-inject jadegate proxy into all detected MCP client configs.

Supports:
- Claude Desktop
- Cursor
- Windsurf
- Cline (VS Code extension)
- Continue
- Zed
- Custom config paths

All operations are reversible via `jadegate uninstall`.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("jadegate.installer")

JADEGATE_MARKER = "__jadegate_protected__"
BACKUP_SUFFIX = ".jadegate-backup"


@dataclass
class MCPClientConfig:
    """A known MCP client and its config location."""
    name: str
    config_paths: List[str]  # platform-dependent candidates
    servers_key: str = "mcpServers"  # JSON key containing server definitions
    nested_path: List[str] = field(default_factory=list)  # for nested configs like VS Code settings


def _expand(path: str) -> str:
    """Expand ~ and env vars."""
    return os.path.expandvars(os.path.expanduser(path))


def _get_known_clients() -> List[MCPClientConfig]:
    """Return all known MCP client configurations."""
    system = platform.system()

    clients = []

    # Claude Desktop
    if system == "Darwin":
        claude_paths = ["~/Library/Application Support/Claude/claude_desktop_config.json"]
    elif system == "Windows":
        claude_paths = ["%APPDATA%/Claude/claude_desktop_config.json"]
    else:
        claude_paths = [
            "~/.config/claude/claude_desktop_config.json",
            "~/.config/Claude/claude_desktop_config.json",
        ]
    clients.append(MCPClientConfig(name="Claude Desktop", config_paths=claude_paths))

    # Cursor
    if system == "Darwin":
        cursor_paths = [
            "~/Library/Application Support/Cursor/mcp.json",
            "~/.cursor/mcp.json",
        ]
    elif system == "Windows":
        cursor_paths = ["%APPDATA%/Cursor/mcp.json", "~/.cursor/mcp.json"]
    else:
        cursor_paths = ["~/.cursor/mcp.json", "~/.config/cursor/mcp.json"]
    clients.append(MCPClientConfig(name="Cursor", config_paths=cursor_paths))

    # Windsurf
    clients.append(MCPClientConfig(
        name="Windsurf",
        config_paths=["~/.windsurf/mcp.json", "~/.config/windsurf/mcp.json"],
    ))

    # Cline (VS Code extension) — nested in VS Code settings
    if system == "Darwin":
        cline_paths = ["~/Library/Application Support/Code/User/settings.json"]
    elif system == "Windows":
        cline_paths = ["%APPDATA%/Code/User/settings.json"]
    else:
        cline_paths = ["~/.config/Code/User/settings.json"]
    clients.append(MCPClientConfig(
        name="Cline",
        config_paths=cline_paths,
        servers_key="mcpServers",
        nested_path=["cline.mcpServers"],
    ))

    # Continue
    clients.append(MCPClientConfig(
        name="Continue",
        config_paths=["~/.continue/config.json"],
        servers_key="mcpServers",
    ))

    # Zed
    if system == "Darwin":
        zed_paths = ["~/Library/Application Support/Zed/settings.json"]
    else:
        zed_paths = ["~/.config/zed/settings.json"]
    clients.append(MCPClientConfig(
        name="Zed",
        config_paths=zed_paths,
        servers_key="mcpServers",
        nested_path=["context_servers"],
    ))

    return clients


@dataclass
class InstallResult:
    """Result of installing jadegate into a client config."""
    client_name: str
    config_path: str
    servers_found: int
    servers_wrapped: int
    already_protected: int
    backup_path: str = ""
    error: str = ""
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client": self.client_name,
            "config": self.config_path,
            "servers_found": self.servers_found,
            "servers_wrapped": self.servers_wrapped,
            "already_protected": self.already_protected,
            "backup": self.backup_path,
            "error": self.error,
            "success": self.success,
        }


def _find_jadegate_binary() -> str:
    """Find the jadegate CLI binary path."""
    # Check common locations
    candidates = [
        shutil.which("jadegate"),
        os.path.expanduser("~/.local/bin/jadegate"),
        os.path.join(os.path.dirname(__file__), "..", "cli.py"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    # Fallback: use python -m jadegate.cli
    return "jadegate"


def _wrap_server_command(server_config: Dict[str, Any], jadegate_bin: str) -> Tuple[bool, bool]:
    """
    Wrap a single MCP server config with jadegate proxy.

    Returns (was_wrapped, was_already_protected).
    """
    # Check if already protected
    if server_config.get(JADEGATE_MARKER):
        return False, True

    cmd = server_config.get("command", "")
    args = server_config.get("args", [])

    if not cmd:
        return False, False

    # Save original
    server_config["_original_command"] = cmd
    server_config["_original_args"] = list(args) if isinstance(args, list) else []

    # Wrap: jadegate proxy <original_command> <original_args>
    original_full = [cmd] + (args if isinstance(args, list) else [])
    server_config["command"] = jadegate_bin
    server_config["args"] = ["proxy"] + original_full
    server_config[JADEGATE_MARKER] = True

    return True, False


def _unwrap_server_command(server_config: Dict[str, Any]) -> bool:
    """Unwrap a jadegate-protected server back to original. Returns True if unwrapped."""
    if not server_config.get(JADEGATE_MARKER):
        return False

    original_cmd = server_config.get("_original_command")
    original_args = server_config.get("_original_args", [])

    if original_cmd:
        server_config["command"] = original_cmd
        server_config["args"] = original_args

    # Clean up markers
    for key in [JADEGATE_MARKER, "_original_command", "_original_args"]:
        server_config.pop(key, None)

    return True


def _get_servers_from_config(data: Dict, client: MCPClientConfig) -> Optional[Dict]:
    """Navigate nested config to find the mcpServers dict."""
    if client.nested_path:
        current = data
        for key in client.nested_path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current if isinstance(current, dict) else None
    return data.get(client.servers_key, None)


class JadeGateInstaller:
    """
    Installs jadegate protection into MCP client configurations.

    Usage:
        installer = JadeGateInstaller()
        results = installer.install()  # auto-detect and protect all clients
        # or
        results = installer.install(config_paths=["/path/to/custom/mcp.json"])
    """

    def __init__(self):
        self._jadegate_bin = _find_jadegate_binary()
        self._known_clients = _get_known_clients()

    def install(self, config_paths: Optional[List[str]] = None) -> List[InstallResult]:
        """
        Install jadegate protection into all detected MCP client configs.

        Args:
            config_paths: Optional list of specific config files to protect.
                         If None, auto-detects all known clients.
        """
        results = []

        if config_paths:
            for path in config_paths:
                expanded = _expand(path)
                if os.path.exists(expanded):
                    result = self._install_config(
                        MCPClientConfig(name="Custom", config_paths=[path]),
                        expanded,
                    )
                    results.append(result)
                else:
                    results.append(InstallResult(
                        client_name="Custom", config_path=expanded,
                        servers_found=0, servers_wrapped=0, already_protected=0,
                        error=f"File not found: {expanded}", success=False,
                    ))
        else:
            for client in self._known_clients:
                for path_template in client.config_paths:
                    path = _expand(path_template)
                    if os.path.exists(path):
                        result = self._install_config(client, path)
                        results.append(result)
                        break  # Only use first found config per client

        return results

    def uninstall(self, config_paths: Optional[List[str]] = None) -> List[InstallResult]:
        """Remove jadegate protection from configs (restore originals)."""
        results = []

        if config_paths:
            targets = [(MCPClientConfig(name="Custom", config_paths=[p]), _expand(p)) for p in config_paths]
        else:
            targets = []
            for client in self._known_clients:
                for path_template in client.config_paths:
                    path = _expand(path_template)
                    if os.path.exists(path):
                        targets.append((client, path))
                        break

        for client, path in targets:
            result = self._uninstall_config(client, path)
            results.append(result)

        return results

    def _install_config(self, client: MCPClientConfig, path: str) -> InstallResult:
        """Install jadegate into a single config file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            servers = _get_servers_from_config(data, client)
            if not servers or not isinstance(servers, dict):
                return InstallResult(
                    client_name=client.name, config_path=path,
                    servers_found=0, servers_wrapped=0, already_protected=0,
                )

            # Backup
            backup_path = path + BACKUP_SUFFIX
            if not os.path.exists(backup_path):
                shutil.copy2(path, backup_path)

            wrapped = 0
            already = 0
            for name, server_conf in servers.items():
                if isinstance(server_conf, dict):
                    was_wrapped, was_already = _wrap_server_command(server_conf, self._jadegate_bin)
                    if was_wrapped:
                        wrapped += 1
                        logger.info("Protected: %s/%s", client.name, name)
                    if was_already:
                        already += 1

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return InstallResult(
                client_name=client.name, config_path=path,
                servers_found=len(servers), servers_wrapped=wrapped,
                already_protected=already, backup_path=backup_path,
            )

        except Exception as e:
            return InstallResult(
                client_name=client.name, config_path=path,
                servers_found=0, servers_wrapped=0, already_protected=0,
                error=str(e), success=False,
            )

    def _uninstall_config(self, client: MCPClientConfig, path: str) -> InstallResult:
        """Remove jadegate from a single config file."""
        try:
            # Try restoring from backup first
            backup_path = path + BACKUP_SUFFIX
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, path)
                os.remove(backup_path)
                return InstallResult(
                    client_name=client.name, config_path=path,
                    servers_found=0, servers_wrapped=0, already_protected=0,
                    backup_path="(restored from backup)",
                )

            # No backup, manually unwrap
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            servers = _get_servers_from_config(data, client)
            if not servers:
                return InstallResult(
                    client_name=client.name, config_path=path,
                    servers_found=0, servers_wrapped=0, already_protected=0,
                )

            unwrapped = 0
            for name, server_conf in servers.items():
                if isinstance(server_conf, dict) and _unwrap_server_command(server_conf):
                    unwrapped += 1

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return InstallResult(
                client_name=client.name, config_path=path,
                servers_found=len(servers), servers_wrapped=unwrapped,
                already_protected=0,
            )

        except Exception as e:
            return InstallResult(
                client_name=client.name, config_path=path,
                servers_found=0, servers_wrapped=0, already_protected=0,
                error=str(e), success=False,
            )

    def status(self) -> List[Dict[str, Any]]:
        """Check which clients are currently protected."""
        statuses = []
        for client in self._known_clients:
            for path_template in client.config_paths:
                path = _expand(path_template)
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        servers = _get_servers_from_config(data, client)
                        if servers:
                            protected = sum(
                                1 for s in servers.values()
                                if isinstance(s, dict) and s.get(JADEGATE_MARKER)
                            )
                            statuses.append({
                                "client": client.name,
                                "config": path,
                                "total_servers": len(servers),
                                "protected": protected,
                                "has_backup": os.path.exists(path + BACKUP_SUFFIX),
                            })
                    except Exception:
                        pass
                    break
        return statuses


# ─── Top-level convenience functions ─────────────────────────

def install_all(extra_configs: Optional[List[str]] = None) -> List[InstallResult]:
    """Install jadegate proxy into all detected MCP client configs."""
    installer = JadeGateInstaller()
    return installer.install(config_paths=extra_configs)


def uninstall_all(extra_configs: Optional[List[str]] = None) -> List[InstallResult]:
    """Remove jadegate proxy from all MCP client configs."""
    installer = JadeGateInstaller()
    return installer.uninstall(config_paths=extra_configs)


def install_status() -> List[Dict[str, Any]]:
    """Check which clients are currently protected."""
    installer = JadeGateInstaller()
    return installer.status()
