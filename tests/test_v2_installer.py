"""Tests for JadeGate Installer — auto-inject into MCP client configs."""

import json
import os
import tempfile
import pytest

from jadegate.installer import (
    install_all, uninstall_all, install_status,
    _wrap_server_command, _unwrap_server_command,
    JADEGATE_MARKER, BACKUP_SUFFIX,
)


class TestWrapUnwrap:
    def test_wrap_server(self):
        config = {"command": "npx", "args": ["@mcp/server-fs", "/tmp"]}
        wrapped, already = _wrap_server_command(config, "jadegate")
        assert wrapped is True
        assert already is False
        assert config["command"] == "jadegate"
        assert config["args"] == ["proxy", "npx", "@mcp/server-fs", "/tmp"]
        assert config[JADEGATE_MARKER] is True

    def test_wrap_already_protected(self):
        config = {"command": "jadegate", "args": ["proxy", "npx", "server"],
                  JADEGATE_MARKER: True}
        wrapped, already = _wrap_server_command(config, "jadegate")
        assert wrapped is False
        assert already is True

    def test_wrap_no_command(self):
        config = {"args": ["something"]}
        wrapped, already = _wrap_server_command(config, "jadegate")
        assert wrapped is False
        assert already is False

    def test_unwrap_server(self):
        config = {
            "command": "jadegate", "args": ["proxy", "npx", "server"],
            JADEGATE_MARKER: True,
            "_original_command": "npx",
            "_original_args": ["server"],
        }
        unwrapped = _unwrap_server_command(config)
        assert unwrapped is True
        assert config["command"] == "npx"
        assert config["args"] == ["server"]
        assert JADEGATE_MARKER not in config

    def test_unwrap_not_protected(self):
        config = {"command": "npx", "args": ["server"]}
        unwrapped = _unwrap_server_command(config)
        assert unwrapped is False

    def test_wrap_then_unwrap_roundtrip(self):
        original = {"command": "node", "args": ["server.js", "--port", "3000"]}
        config = dict(original)
        _wrap_server_command(config, "jadegate")
        assert config["command"] == "jadegate"
        _unwrap_server_command(config)
        assert config["command"] == "node"
        assert config["args"] == ["server.js", "--port", "3000"]


class TestInstallWithConfig:
    def test_install_claude_desktop_config(self):
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
            results = install_all(extra_configs=[path])
            # Should find and wrap the servers from extra config
            custom_results = [r for r in results if r.config_path == path]
            if custom_results:
                r = custom_results[0]
                assert r.success
                assert r.servers_found == 2
                assert r.servers_wrapped == 2

                # Verify the file was modified
                with open(path) as f:
                    modified = json.load(f)
                for name, srv in modified["mcpServers"].items():
                    assert srv.get(JADEGATE_MARKER) is True
                    assert srv["command"] == "jadegate"
                    assert srv["args"][0] == "proxy"

                # Verify backup exists
                assert os.path.exists(path + BACKUP_SUFFIX)
        finally:
            os.unlink(path)
            if os.path.exists(path + BACKUP_SUFFIX):
                os.unlink(path + BACKUP_SUFFIX)

    def test_install_then_uninstall(self):
        config = {
            "mcpServers": {
                "test": {"command": "echo", "args": ["hello"]},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            path = f.name
        try:
            # Install
            install_all(extra_configs=[path])
            with open(path) as f:
                data = json.load(f)
            assert data["mcpServers"]["test"]["command"] == "jadegate"

            # Uninstall
            uninstall_all(extra_configs=[path])
            with open(path) as f:
                data = json.load(f)
            assert data["mcpServers"]["test"]["command"] == "echo"
            assert data["mcpServers"]["test"]["args"] == ["hello"]
            assert JADEGATE_MARKER not in data["mcpServers"]["test"]
        finally:
            os.unlink(path)
            if os.path.exists(path + BACKUP_SUFFIX):
                os.unlink(path + BACKUP_SUFFIX)

    def test_install_idempotent(self):
        config = {
            "mcpServers": {
                "test": {"command": "echo", "args": ["hello"]},
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            path = f.name
        try:
            r1 = install_all(extra_configs=[path])
            r2 = install_all(extra_configs=[path])
            custom_r2 = [r for r in r2 if r.config_path == path]
            if custom_r2:
                assert custom_r2[0].servers_wrapped == 0
                assert custom_r2[0].already_protected == 1
        finally:
            os.unlink(path)
            if os.path.exists(path + BACKUP_SUFFIX):
                os.unlink(path + BACKUP_SUFFIX)

    def test_install_status(self):
        # install_status() only checks known client paths, not extra configs
        # Just verify it returns a list without error
        statuses = install_status()
        assert isinstance(statuses, list)
