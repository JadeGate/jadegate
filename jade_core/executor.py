"""
💠 JadeGate DAG Executor
========================
Execute verified skill DAGs in a sandboxed environment.

Features:
- Topological execution order
- Node-level timeout enforcement
- Template variable resolution
- Sandboxed HTTP calls (whitelist-only)
- Result propagation between nodes
- Execution trace for debugging
"""

import json
import time
import hashlib
import re
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque


@dataclass
class NodeResult:
    node_id: str
    status: str  # "success" | "error" | "skipped" | "timeout"
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class ExecutionTrace:
    skill_id: str
    started_at: float
    finished_at: float = 0
    status: str = "running"  # "running" | "completed" | "failed"
    node_results: List[NodeResult] = field(default_factory=list)
    total_duration_ms: float = 0

    def to_dict(self):
        return {
            "skill_id": self.skill_id,
            "status": self.status,
            "total_duration_ms": self.total_duration_ms,
            "nodes": [
                {
                    "id": r.node_id,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "output": r.output if r.status == "success" else None,
                    "error": r.error,
                }
                for r in self.node_results
            ],
        }


class ExecutionError(Exception):
    pass


class SandboxViolation(ExecutionError):
    pass


class JadeExecutor:
    """Execute verified JADE skill DAGs."""

    def __init__(self, verify_before_run: bool = True, dry_run: bool = False):
        self.verify_before_run = verify_before_run
        self.dry_run = dry_run
        self._node_handlers = {
            "http_get": self._exec_http_get,
            "http_post": self._exec_http_post,
            "json_extract": self._exec_json_extract,
            "json_transform": self._exec_json_transform,
            "template_render": self._exec_template_render,
            "conditional": self._exec_conditional,
            "aggregate": self._exec_aggregate,
            "return": self._exec_return,
        }

    def execute(
        self,
        skill: Dict,
        inputs: Dict[str, Any],
        timeout_ms: Optional[int] = None,
    ) -> ExecutionTrace:
        """Execute a skill DAG with given inputs."""

        skill_id = skill.get("skill_id", "unknown")
        trace = ExecutionTrace(skill_id=skill_id, started_at=time.time())

        # 1. Verify if enabled
        if self.verify_before_run:
            from jade_core.validator import JadeValidator
            v = JadeValidator()
            result = v.validate(skill)
            if not result.valid:
                errors = [i.message for i in result.issues if i.severity.value == "error"]
                trace.status = "failed"
                trace.finished_at = time.time()
                raise ExecutionError(f"Skill failed verification: {errors}")

        # 2. Extract DAG
        dag = skill.get("execution_dag", {})
        nodes = {n["id"]: n for n in dag.get("nodes", [])}
        edges = dag.get("edges", [])

        # 3. Build adjacency + in-degree for topological sort
        adj: Dict[str, List[str]] = {nid: [] for nid in nodes}
        in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
        for edge in edges:
            src, dst = edge["from"], edge["to"]
            adj[src].append(dst)
            in_degree[dst] = in_degree.get(dst, 0) + 1

        # 4. Topological sort (Kahn's algorithm)
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        exec_order = []
        while queue:
            nid = queue.popleft()
            exec_order.append(nid)
            for neighbor in adj.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(exec_order) != len(nodes):
            trace.status = "failed"
            raise ExecutionError("Cycle detected in DAG")

        # 5. Security context
        security = skill.get("security", {})
        whitelist = set(security.get("network_whitelist", []))
        max_time = timeout_ms or security.get("max_execution_time_ms", 30000)

        # 6. Execute nodes in order
        context = {"input": inputs, "nodes": {}, "env": {}}
        start_time = time.time()

        for nid in exec_order:
            elapsed = (time.time() - start_time) * 1000
            if elapsed > max_time:
                trace.status = "failed"
                trace.node_results.append(NodeResult(
                    node_id=nid, status="timeout",
                    error=f"Global timeout {max_time}ms exceeded"
                ))
                break

            node = nodes[nid]
            node_start = time.time()

            try:
                if self.dry_run:
                    output = {"_dry_run": True, "node_id": nid, "action": node.get("action", "unknown")}
                else:
                    output = self._execute_node(node, context, whitelist)

                duration = (time.time() - node_start) * 1000
                context["nodes"][nid] = output

                trace.node_results.append(NodeResult(
                    node_id=nid, status="success",
                    output=output, duration_ms=round(duration, 2)
                ))

            except SandboxViolation as e:
                duration = (time.time() - node_start) * 1000
                trace.node_results.append(NodeResult(
                    node_id=nid, status="error",
                    error=f"SANDBOX: {e}", duration_ms=round(duration, 2)
                ))
                trace.status = "failed"
                break

            except Exception as e:
                duration = (time.time() - node_start) * 1000
                trace.node_results.append(NodeResult(
                    node_id=nid, status="error",
                    error=str(e), duration_ms=round(duration, 2)
                ))
                # Continue or fail based on node config
                if node.get("required", True):
                    trace.status = "failed"
                    break

        else:
            trace.status = "completed"

        trace.finished_at = time.time()
        trace.total_duration_ms = round((trace.finished_at - trace.started_at) * 1000, 2)
        return trace

    def _execute_node(self, node: Dict, context: Dict, whitelist: set) -> Any:
        """Execute a single DAG node."""
        action = node.get("action", node.get("type", "unknown"))
        handler = self._node_handlers.get(action)

        if handler:
            return handler(node, context, whitelist)

        # Unknown action type — try generic param resolution
        params = self._resolve_params(node.get("params", {}), context)
        return {"_unhandled_action": action, "params": params}

    def _resolve_template(self, template: str, context: Dict) -> str:
        """Resolve {{var}} templates against context."""
        def replacer(match):
            path = match.group(1).strip()
            parts = path.split(".")
            val = context
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p, "")
                else:
                    return match.group(0)
            return str(val) if not isinstance(val, str) else val
        return re.sub(r"\{\{([^}]+)\}\}", replacer, template)

    def _resolve_params(self, params: Dict, context: Dict) -> Dict:
        """Resolve all template strings in params."""
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str):
                resolved[k] = self._resolve_template(v, context)
            elif isinstance(v, dict):
                resolved[k] = self._resolve_params(v, context)
            elif isinstance(v, list):
                resolved[k] = [
                    self._resolve_template(i, context) if isinstance(i, str) else i
                    for i in v
                ]
            else:
                resolved[k] = v
        return resolved

    def _check_domain(self, url: str, whitelist: set):
        """Verify URL domain is in whitelist."""
        if "*" in whitelist:
            return
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        for allowed in whitelist:
            if domain == allowed:
                return
            if allowed.startswith("*.") and domain.endswith(allowed[1:]):
                return
        raise SandboxViolation(f"Domain '{domain}' not in whitelist: {whitelist}")

    # === Node Handlers ===

    def _exec_http_get(self, node: Dict, context: Dict, whitelist: set) -> Any:
        params = self._resolve_params(node.get("params", {}), context)
        url = params.get("url", "")
        self._check_domain(url, whitelist)

        headers = params.get("headers", {})
        req = urllib.request.Request(url, headers=headers)
        timeout = node.get("timeout_ms", 10000) / 1000

        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")

        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"_raw": body, "_status": resp.status}

    def _exec_http_post(self, node: Dict, context: Dict, whitelist: set) -> Any:
        params = self._resolve_params(node.get("params", {}), context)
        url = params.get("url", "")
        self._check_domain(url, whitelist)

        headers = params.get("headers", {"Content-Type": "application/json"})
        body = params.get("body", {})
        data = json.dumps(body).encode() if isinstance(body, dict) else str(body).encode()

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        timeout = node.get("timeout_ms", 10000) / 1000

        resp = urllib.request.urlopen(req, timeout=timeout)
        resp_body = resp.read().decode("utf-8", errors="replace")

        try:
            return json.loads(resp_body)
        except json.JSONDecodeError:
            return {"_raw": resp_body, "_status": resp.status}

    def _exec_json_extract(self, node: Dict, context: Dict, whitelist: set) -> Any:
        params = self._resolve_params(node.get("params", {}), context)
        source_path = params.get("source", "")
        field_path = params.get("field", "")

        # Navigate to source
        parts = source_path.split(".")
        val = context
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p, {})

        # Extract field
        if field_path:
            for p in field_path.split("."):
                if isinstance(val, dict):
                    val = val.get(p, None)
                elif isinstance(val, list) and p.isdigit():
                    val = val[int(p)] if int(p) < len(val) else None

        return val

    def _exec_json_transform(self, node: Dict, context: Dict, whitelist: set) -> Any:
        params = self._resolve_params(node.get("params", {}), context)
        mapping = params.get("mapping", {})
        result = {}
        for out_key, source_expr in mapping.items():
            if isinstance(source_expr, str) and source_expr.startswith("{{"):
                result[out_key] = self._resolve_template(source_expr, context)
            else:
                result[out_key] = source_expr
        return result

    def _exec_template_render(self, node: Dict, context: Dict, whitelist: set) -> Any:
        params = self._resolve_params(node.get("params", {}), context)
        template = params.get("template", "")
        return self._resolve_template(template, context)

    def _exec_conditional(self, node: Dict, context: Dict, whitelist: set) -> Any:
        params = self._resolve_params(node.get("params", {}), context)
        condition = params.get("condition", "")
        then_val = params.get("then", None)
        else_val = params.get("else", None)

        # Simple condition evaluation (no eval!)
        # Supports: "{{x}} == value", "{{x}} != value", "{{x}} > N"
        resolved = self._resolve_template(condition, context)
        parts = re.split(r"\s*(==|!=|>=|<=|>|<)\s*", resolved, maxsplit=1)

        if len(parts) == 3:
            left, op, right = parts[0].strip(), parts[1], parts[2].strip()
            try:
                left_n, right_n = float(left), float(right)
                result = {
                    "==": left_n == right_n, "!=": left_n != right_n,
                    ">": left_n > right_n, "<": left_n < right_n,
                    ">=": left_n >= right_n, "<=": left_n <= right_n,
                }.get(op, False)
            except ValueError:
                result = {"==": left == right, "!=": left != right}.get(op, False)
        else:
            result = bool(resolved and resolved.lower() not in ("false", "0", "null", "none", ""))

        return then_val if result else else_val

    def _exec_aggregate(self, node: Dict, context: Dict, whitelist: set) -> Any:
        params = self._resolve_params(node.get("params", {}), context)
        sources = params.get("sources", [])
        result = {}
        for src in sources:
            if isinstance(src, str):
                parts = src.split(".")
                val = context
                for p in parts:
                    if isinstance(val, dict):
                        val = val.get(p, {})
                result[src.split(".")[-1]] = val
        return result

    def _exec_return(self, node: Dict, context: Dict, whitelist: set) -> Any:
        params = self._resolve_params(node.get("params", {}), context)
        return params
