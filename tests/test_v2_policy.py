"""Tests for JadeGate v2 Policy Layer."""

import json
import os
import tempfile
import pytest

from jadegate.policy.policy import JadePolicy


class TestJadePolicy:
    def test_default_policy(self):
        p = JadePolicy.default()
        assert p.max_calls_per_minute == 60
        assert p.max_call_depth == 20
        assert p.enable_dangerous_pattern_scan is True
        assert "shell_exec" in p.blocked_actions
        assert "email_send" in p.require_human_approval

    def test_strict_policy(self):
        p = JadePolicy.strict()
        assert p.max_calls_per_minute == 20
        assert "http_post" in p.blocked_actions
        assert "http_get" in p.require_human_approval

    def test_permissive_policy(self):
        p = JadePolicy.permissive()
        assert "*" in p.network_whitelist
        assert "*" in p.file_read_paths
        assert p.max_calls_per_minute == 300

    def test_action_blocked(self):
        p = JadePolicy.default()
        assert p.is_action_blocked("shell_exec") is True
        assert p.is_action_blocked("file_read") is False

    def test_needs_approval(self):
        p = JadePolicy.default()
        assert p.needs_approval("email_send") is True
        assert p.needs_approval("file_read") is False

    def test_domain_allowed_empty_whitelist(self):
        p = JadePolicy.default()
        # Empty whitelist = allow all (except blocked)
        assert p.is_domain_allowed("example.com") is True
        assert p.is_domain_allowed("169.254.169.254") is False

    def test_domain_allowed_with_whitelist(self):
        p = JadePolicy(network_whitelist=["api.github.com", "*.openai.com"])
        assert p.is_domain_allowed("api.github.com") is True
        assert p.is_domain_allowed("api.openai.com") is True
        assert p.is_domain_allowed("evil.com") is False

    def test_domain_wildcard(self):
        p = JadePolicy(network_whitelist=["*"])
        assert p.is_domain_allowed("anything.com") is True
        # But blocked domains are still blocked
        assert p.is_domain_allowed("169.254.169.254") is False

    def test_file_path_allowed(self):
        p = JadePolicy(file_read_paths=["/tmp/*", "/home/user/docs/*"])
        assert p.is_file_path_allowed("/tmp/data.txt", "read") is True
        assert p.is_file_path_allowed("/etc/shadow", "read") is False

    def test_from_dict(self):
        data = {
            "max_calls_per_minute": 100,
            "blocked_actions": ["shell_exec", "custom_action"],
            "network_whitelist": ["api.example.com"],
        }
        p = JadePolicy.from_dict(data)
        assert p.max_calls_per_minute == 100
        assert "custom_action" in p.blocked_actions
        assert "api.example.com" in p.network_whitelist

    def test_from_file(self):
        data = {"jadegate_policy": {"max_calls_per_minute": 42}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            p = JadePolicy.from_file(path)
            assert p.max_calls_per_minute == 42
        finally:
            os.unlink(path)

    def test_save_and_load(self):
        p = JadePolicy(max_calls_per_minute=77, blocked_actions=["test_action"])
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            p.save(path)
            loaded = JadePolicy.from_file(path)
            assert loaded.max_calls_per_minute == 77
            assert "test_action" in loaded.blocked_actions
        finally:
            os.unlink(path)

    def test_merge(self):
        base = JadePolicy.default()
        override = JadePolicy(
            max_calls_per_minute=120,
            blocked_actions=["custom_block"],
        )
        merged = base.merge(override)
        assert merged.max_calls_per_minute == 120
        assert "shell_exec" in merged.blocked_actions  # from base
        assert "custom_block" in merged.blocked_actions  # from override

    def test_to_dict(self):
        p = JadePolicy.default()
        d = p.to_dict()
        assert "max_calls_per_minute" in d
        assert "blocked_actions" in d
        assert isinstance(d["blocked_actions"], list)
