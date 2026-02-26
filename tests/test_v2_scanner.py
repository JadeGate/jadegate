"""Tests for JadeGate v2 Scanner."""

import json
import os
import tempfile
import pytest

from jadegate.scanner.mcp_scanner import MCPScanner, MCPServerInfo, _parse_mcp_config
from jadegate.scanner.report import ScanReport
from jadegate.trust.certificate import RiskProfile


class TestMCPConfigParsing:
    def test_parse_claude_desktop_config(self):
        config = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["@modelcontextprotocol/server-filesystem", "/tmp"],
                },
                "github": {
                    "command": "npx",
                    "args": ["@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "xxx"},
                },
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            path = f.name
        try:
            servers = _parse_mcp_config(path, "claude_desktop")
            assert len(servers) == 2
            assert servers[0].name == "filesystem"
            assert servers[0].command == ["npx", "@modelcontextprotocol/server-filesystem", "/tmp"]
            assert servers[1].name == "github"
            assert servers[1].source == "claude_desktop"
        finally:
            os.unlink(path)

    def test_parse_empty_config(self):
        config = {"mcpServers": {}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            path = f.name
        try:
            servers = _parse_mcp_config(path, "test")
            assert len(servers) == 0
        finally:
            os.unlink(path)

    def test_parse_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            path = f.name
        try:
            servers = _parse_mcp_config(path, "test")
            assert len(servers) == 0
        finally:
            os.unlink(path)


class TestMCPScanner:
    def test_discover_no_configs(self):
        scanner = MCPScanner()
        # May or may not find configs depending on environment
        servers = scanner.discover()
        assert isinstance(servers, list)

    def test_assess_server_by_command(self):
        scanner = MCPScanner()
        server = MCPServerInfo(
            name="filesystem",
            command=["npx", "@modelcontextprotocol/server-filesystem", "/tmp"],
            source="test",
        )
        assessed = scanner.assess_server(server, probe=False)
        assert assessed.risk_profile is not None
        assert assessed.risk_profile.file_access is True

    def test_assess_shell_server(self):
        scanner = MCPScanner()
        server = MCPServerInfo(
            name="shell",
            command=["npx", "mcp-shell-server"],
            source="test",
        )
        assessed = scanner.assess_server(server, probe=False)
        assert assessed.risk_profile.level in ("high", "critical")

    def test_assess_all(self):
        scanner = MCPScanner()
        servers = [
            MCPServerInfo(name="a", command=["npx", "server-a"], source="test"),
            MCPServerInfo(name="b", command=["npx", "server-b"], source="test"),
        ]
        assessed = scanner.assess_all(servers, probe=False)
        assert len(assessed) == 2
        assert all(s.risk_profile is not None for s in assessed)


class TestScanReport:
    def test_empty_report(self):
        report = ScanReport([])
        terminal = report.to_terminal()
        assert "No MCP servers found" in terminal

    def test_report_with_servers(self):
        servers = [
            MCPServerInfo(
                name="filesystem",
                command=["npx", "server-fs"],
                source="test",
                risk_profile=RiskProfile(level="medium", file_access=True),
            ),
            MCPServerInfo(
                name="shell",
                command=["npx", "server-shell"],
                source="test",
                risk_profile=RiskProfile(level="critical", shell_access=True),
            ),
        ]
        report = ScanReport(servers)
        terminal = report.to_terminal()
        assert "filesystem" in terminal
        assert "shell" in terminal

    def test_to_json(self):
        servers = [
            MCPServerInfo(
                name="test",
                command=["echo"],
                source="test",
                risk_profile=RiskProfile(level="low"),
            ),
        ]
        report = ScanReport(servers)
        j = report.to_json()
        data = json.loads(j)
        assert "jadegate_scan_report" in data
        assert data["jadegate_scan_report"]["total_servers"] == 1

    def test_save_json(self):
        servers = [
            MCPServerInfo(name="t", command=["x"], source="test",
                         risk_profile=RiskProfile(level="low")),
        ]
        report = ScanReport(servers)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            report.save_json(path)
            with open(path) as f:
                data = json.load(f)
            assert "jadegate_scan_report" in data
        finally:
            os.unlink(path)
