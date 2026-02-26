"""Tests for JadeGate v2 Trust Layer."""

import json
import os
import tempfile
import time
import pytest

from jadegate.trust.certificate import JadeCertificate, RiskProfile
from jadegate.trust.trust_store import LocalTrustStore
from jadegate.trust.tofu import TrustOnFirstUse, TOFUAlert


class TestRiskProfile:
    def test_from_tool_info_shell(self):
        rp = RiskProfile.from_tool_info("run_command", "Execute shell commands")
        assert rp.level == "critical"
        assert rp.shell_access is True

    def test_from_tool_info_network_file(self):
        rp = RiskProfile.from_tool_info("upload_file", "Read file and send via HTTP")
        assert rp.level == "high"
        assert rp.network_access is True
        assert rp.file_access is True

    def test_from_tool_info_read_only(self):
        rp = RiskProfile.from_tool_info("search_docs", "Search documentation")
        assert rp.level == "low"

    def test_from_tool_info_network(self):
        rp = RiskProfile.from_tool_info("fetch_url", "Fetch content from URL")
        assert rp.network_access is True
        assert rp.level == "medium"

    def test_to_dict_roundtrip(self):
        rp = RiskProfile(level="high", capabilities=["network"], network_access=True)
        d = rp.to_dict()
        rp2 = RiskProfile.from_dict(d)
        assert rp2.level == "high"
        assert rp2.network_access is True


class TestJadeCertificate:
    def test_create(self):
        cert = JadeCertificate(tool_id="test_tool", display_name="Test Tool")
        assert cert.tool_id == "test_tool"
        assert cert.trust_score == 0.5

    def test_update_trust_success(self):
        cert = JadeCertificate(tool_id="t1")
        score = cert.update_trust(success=True)
        assert score > 0.5  # should increase

    def test_update_trust_failure(self):
        cert = JadeCertificate(tool_id="t1")
        score = cert.update_trust(success=False)
        assert score < 0.5  # should decrease

    def test_bayesian_convergence(self):
        cert = JadeCertificate(tool_id="t1")
        for _ in range(20):
            cert.update_trust(success=True)
        assert cert.trust_score > 0.9

    def test_fingerprint(self):
        cert = JadeCertificate(tool_id="t1", display_name="Test")
        fp = cert.compute_fingerprint()
        assert len(fp) == 32
        # Same content = same fingerprint
        cert2 = JadeCertificate(tool_id="t1", display_name="Test")
        assert cert2.compute_fingerprint() == fp

    def test_to_dict_from_dict(self):
        cert = JadeCertificate(
            tool_id="t1",
            display_name="Test",
            risk_profile=RiskProfile(level="medium", network_access=True),
            trust_score=0.75,
        )
        d = cert.to_dict()
        cert2 = JadeCertificate.from_dict(d)
        assert cert2.tool_id == "t1"
        assert cert2.trust_score == 0.75
        assert cert2.risk_profile.level == "medium"


class TestLocalTrustStore:
    def test_save_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            cert = JadeCertificate(tool_id="test_tool", display_name="Test")
            store.save(cert)
            loaded = store.get("test_tool")
            assert loaded is not None
            assert loaded.tool_id == "test_tool"

    def test_list_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            store.save(JadeCertificate(tool_id="t1"))
            store.save(JadeCertificate(tool_id="t2"))
            assert len(store.list_all()) == 2

    def test_remove(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            store.save(JadeCertificate(tool_id="t1"))
            assert store.remove("t1") is True
            assert store.get("t1") is None

    def test_is_trusted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            cert = JadeCertificate(tool_id="t1", trust_score=0.8)
            store.save(cert)
            assert store.is_trusted("t1", min_score=0.6) is True
            assert store.is_trusted("t1", min_score=0.9) is False
            assert store.is_trusted("nonexistent") is False

    def test_update_trust(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            store.save(JadeCertificate(tool_id="t1"))
            new_score = store.update_trust("t1", success=True)
            assert new_score is not None
            assert new_score > 0.5

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = LocalTrustStore(trust_dir=tmpdir)
            store1.save(JadeCertificate(tool_id="t1", display_name="Persistent"))
            # New store instance should load from disk
            store2 = LocalTrustStore(trust_dir=tmpdir)
            loaded = store2.get("t1")
            assert loaded is not None
            assert loaded.display_name == "Persistent"

    def test_get_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            store.save(JadeCertificate(tool_id="t1", trust_score=0.9))
            store.save(JadeCertificate(tool_id="t2", trust_score=0.3,
                       risk_profile=RiskProfile(level="high")))
            summary = store.get_summary()
            assert summary["total_certificates"] == 2
            assert summary["high_risk"] == 1


class TestTOFU:
    def test_first_encounter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            tofu = TrustOnFirstUse(trust_store=store)
            alerts = tofu.check_tool("new_tool", name="New Tool", description="Does stuff")
            assert len(alerts) == 1
            assert alerts[0].alert_type == "new_tool"
            # Should be stored now
            assert store.get("new_tool") is not None

    def test_second_encounter_no_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            tofu = TrustOnFirstUse(trust_store=store)
            tofu.check_tool("tool_a", name="Tool A", description="Read files")
            alerts = tofu.check_tool("tool_a", name="Tool A", description="Read files")
            # No change = no alerts (except maybe new_tool on first)
            assert all(a.alert_type != "risk_escalation" for a in alerts)

    def test_risk_escalation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            tofu = TrustOnFirstUse(trust_store=store)
            # First: low risk
            tofu.check_tool("tool_a", name="Tool A", description="Search documents")
            # Second: now with shell access
            alerts = tofu.check_tool("tool_a", name="Tool A", description="Execute shell commands")
            escalation = [a for a in alerts if a.alert_type == "risk_escalation"]
            assert len(escalation) > 0

    def test_capability_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            tofu = TrustOnFirstUse(trust_store=store)
            tofu.check_tool("tool_a", name="Tool A", description="Read files")
            alerts = tofu.check_tool("tool_a", name="Tool A", description="Read files and send HTTP requests")
            cap_change = [a for a in alerts if a.alert_type == "capability_change"]
            assert len(cap_change) > 0

    def test_reset_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalTrustStore(trust_dir=tmpdir)
            tofu = TrustOnFirstUse(trust_store=store)
            tofu.check_tool("tool_a", name="Tool A", description="test")
            assert tofu.reset_baseline("tool_a") is True
            assert store.get("tool_a") is None
            # Next check should be "new_tool" again
            alerts = tofu.check_tool("tool_a", name="Tool A", description="test")
            assert alerts[0].alert_type == "new_tool"
