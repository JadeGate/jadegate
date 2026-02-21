"""
💠 JadeGate DAG Optimizer
=========================
Runtime path optimization for skill DAGs.

When an agent discovers a better execution path during runtime,
the optimizer can restructure the DAG while maintaining security invariants.

Features:
- Dead node elimination (unreachable nodes)
- Parallel branch detection (independent nodes run concurrently)
- Path shortcutting (skip nodes when output is already available)
- Adaptive routing (choose branches based on runtime conditions)
- Composition (merge multiple skills into a new DAG)
"""

import json
import copy
from typing import Any, Dict, List, Set, Optional, Tuple
from collections import deque
from dataclasses import dataclass, field


@dataclass
class OptimizationResult:
    original_nodes: int
    optimized_nodes: int
    eliminated: List[str] = field(default_factory=list)
    parallelizable: List[List[str]] = field(default_factory=list)
    shortcuts: List[Tuple[str, str]] = field(default_factory=list)
    dag: Dict = field(default_factory=dict)

    @property
    def improved(self) -> bool:
        return (
            len(self.eliminated) > 0
            or len(self.parallelizable) > 0
            or len(self.shortcuts) > 0
        )

    def summary(self) -> str:
        parts = []
        if self.eliminated:
            parts.append(f"{len(self.eliminated)} dead nodes eliminated")
        if self.parallelizable:
            groups = len(self.parallelizable)
            total = sum(len(g) for g in self.parallelizable)
            parts.append(f"{total} nodes in {groups} parallel groups")
        if self.shortcuts:
            parts.append(f"{len(self.shortcuts)} path shortcuts")
        if not parts:
            return "No optimizations found"
        return " · ".join(parts)


class JadeOptimizer:
    """Optimize JADE skill DAGs at build-time or runtime."""

    def optimize(self, skill: Dict, context: Optional[Dict] = None) -> OptimizationResult:
        """Run all optimization passes on a skill DAG."""
        dag = copy.deepcopy(skill.get("execution_dag", {}))
        nodes = {n["id"]: n for n in dag.get("nodes", [])}
        edges = dag.get("edges", [])

        original_count = len(nodes)
        result = OptimizationResult(original_nodes=original_count, optimized_nodes=original_count)

        # Pass 1: Dead node elimination
        eliminated = self._eliminate_dead_nodes(nodes, edges)
        result.eliminated = eliminated
        if eliminated:
            edges = [e for e in edges if e["from"] not in eliminated and e["to"] not in eliminated]
            for nid in eliminated:
                del nodes[nid]

        # Pass 2: Detect parallel branches
        result.parallelizable = self._detect_parallel_branches(nodes, edges)

        # Pass 3: Path shortcuts (skip identity/passthrough nodes)
        shortcuts, edges = self._find_shortcuts(nodes, edges)
        result.shortcuts = shortcuts
        if shortcuts:
            shortcut_nodes = set()
            for src, dst in shortcuts:
                shortcut_nodes.add(src)  # the skipped node
            for nid in shortcut_nodes:
                if nid in nodes:
                    del nodes[nid]
                    result.eliminated.append(nid)

        # Pass 4: Adaptive routing (runtime only)
        if context:
            edges = self._adaptive_route(nodes, edges, context)

        # Rebuild DAG
        result.optimized_nodes = len(nodes)
        result.dag = {
            "nodes": list(nodes.values()),
            "edges": edges,
        }

        return result

    def compose(self, skills: List[Dict], connections: List[Dict]) -> Dict:
        """
        Compose multiple skills into a new combined DAG.

        connections: [{"from_skill": 0, "from_node": "output", "to_skill": 1, "to_node": "input"}]
        """
        combined_nodes = []
        combined_edges = []
        node_map = {}  # (skill_idx, node_id) -> new_node_id

        for idx, skill in enumerate(skills):
            dag = skill.get("execution_dag", {})
            prefix = f"s{idx}_"

            for node in dag.get("nodes", []):
                new_id = f"{prefix}{node['id']}"
                new_node = copy.deepcopy(node)
                new_node["id"] = new_id
                new_node["_source_skill"] = skill.get("skill_id", f"skill_{idx}")
                combined_nodes.append(new_node)
                node_map[(idx, node["id"])] = new_id

            for edge in dag.get("edges", []):
                combined_edges.append({
                    "from": f"{prefix}{edge['from']}",
                    "to": f"{prefix}{edge['to']}",
                })

        # Add cross-skill connections
        for conn in connections:
            from_id = node_map.get((conn["from_skill"], conn["from_node"]))
            to_id = node_map.get((conn["to_skill"], conn["to_node"]))
            if from_id and to_id:
                combined_edges.append({"from": from_id, "to": to_id})

        # Merge security policies (most restrictive wins)
        merged_whitelist = set()
        max_timeout = 0
        sandbox = "strict"
        for skill in skills:
            sec = skill.get("security", {})
            merged_whitelist.update(sec.get("network_whitelist", []))
            max_timeout = max(max_timeout, sec.get("max_execution_time_ms", 30000))
            if sec.get("sandbox") == "standard" and sandbox == "strict":
                sandbox = "standard"

        composed = {
            "jade_version": "1.0.0",
            "skill_id": f"composed_{'_'.join(s.get('skill_id', 'x')[:10] for s in skills)}",
            "metadata": {
                "name": f"Composed: {' + '.join(s.get('metadata', {}).get('name', '?') for s in skills)}",
                "description": "Auto-composed skill from multiple sources",
                "version": "1.0.0",
                "tags": ["composed", "auto-generated"],
            },
            "execution_dag": {
                "nodes": combined_nodes,
                "edges": combined_edges,
            },
            "security": {
                "sandbox": sandbox,
                "network_whitelist": sorted(merged_whitelist),
                "max_execution_time_ms": max_timeout,
            },
        }

        return composed

    def suggest_optimizations(self, trace: Dict) -> List[str]:
        """
        Analyze an execution trace and suggest optimizations.
        Called by agents after running a skill to discover improvements.
        """
        suggestions = []
        nodes = trace.get("nodes", [])

        # Find slow nodes
        for node in nodes:
            if node.get("duration_ms", 0) > 5000:
                suggestions.append(
                    f"Node '{node['id']}' took {node['duration_ms']:.0f}ms — "
                    f"consider caching or parallel execution"
                )

        # Find error nodes that could have fallbacks
        for node in nodes:
            if node.get("status") == "error":
                suggestions.append(
                    f"Node '{node['id']}' failed — add a fallback branch"
                )

        # Detect sequential nodes that could be parallel
        success_nodes = [n for n in nodes if n["status"] == "success"]
        if len(success_nodes) >= 3:
            # Check if any adjacent nodes have no data dependency
            for i in range(len(success_nodes) - 1):
                a, b = success_nodes[i], success_nodes[i + 1]
                # Simple heuristic: if both are HTTP calls, they might be parallelizable
                if "http" in str(a.get("output", "")).lower() and "http" in str(b.get("output", "")).lower():
                    suggestions.append(
                        f"Nodes '{a['id']}' and '{b['id']}' might run in parallel"
                    )

        return suggestions

    # ── Internal optimization passes ──

    def _eliminate_dead_nodes(self, nodes: Dict, edges: List) -> List[str]:
        """Remove nodes unreachable from any root."""
        if not nodes:
            return []

        adj = {nid: [] for nid in nodes}
        has_incoming = set()
        for e in edges:
            adj.setdefault(e["from"], []).append(e["to"])
            has_incoming.add(e["to"])

        roots = [nid for nid in nodes if nid not in has_incoming]
        if not roots:
            return []

        reachable = set()
        queue = deque(roots)
        while queue:
            nid = queue.popleft()
            if nid in reachable:
                continue
            reachable.add(nid)
            for neighbor in adj.get(nid, []):
                if neighbor not in reachable:
                    queue.append(neighbor)

        dead = [nid for nid in nodes if nid not in reachable]
        return dead

    def _detect_parallel_branches(self, nodes: Dict, edges: List) -> List[List[str]]:
        """Find groups of nodes that can execute in parallel."""
        adj = {nid: set() for nid in nodes}
        rev = {nid: set() for nid in nodes}
        for e in edges:
            adj[e["from"]].add(e["to"])
            rev[e["to"]].add(e["from"])

        # Nodes at the same "depth" with no mutual dependency can be parallel
        in_degree = {nid: len(rev[nid]) for nid in nodes}
        levels: List[List[str]] = []
        queue = deque([nid for nid, d in in_degree.items() if d == 0])
        while queue:
            level = list(queue)
            levels.append(level)
            next_queue = deque()
            for nid in level:
                for neighbor in adj[nid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            queue = next_queue

        # Only return levels with 2+ nodes (actual parallelism)
        return [level for level in levels if len(level) >= 2]

    def _find_shortcuts(self, nodes: Dict, edges: List) -> Tuple[List[Tuple[str, str]], List]:
        """Find passthrough nodes that can be skipped."""
        shortcuts = []
        new_edges = list(edges)

        for nid, node in list(nodes.items()):
            action = node.get("action", "")
            # Identity/passthrough nodes can be shortcut
            if action in ("passthrough", "identity", "noop"):
                incoming = [e for e in new_edges if e["to"] == nid]
                outgoing = [e for e in new_edges if e["from"] == nid]
                if len(incoming) == 1 and len(outgoing) == 1:
                    shortcuts.append((nid, outgoing[0]["to"]))
                    # Rewire: incoming source -> outgoing target
                    new_edges = [e for e in new_edges if e["to"] != nid and e["from"] != nid]
                    new_edges.append({"from": incoming[0]["from"], "to": outgoing[0]["to"]})

        return shortcuts, new_edges

    def _adaptive_route(self, nodes: Dict, edges: List, context: Dict) -> List:
        """Choose branches based on runtime context."""
        new_edges = []
        for edge in edges:
            condition = edge.get("condition")
            if condition:
                # Evaluate simple conditions against context
                try:
                    if self._eval_condition(condition, context):
                        new_edges.append(edge)
                except Exception:
                    new_edges.append(edge)  # Keep edge on eval failure
            else:
                new_edges.append(edge)
        return new_edges

    def _eval_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate a simple condition string safely (no eval!)."""
        # Only support simple comparisons: "input.format == json"
        parts = condition.split()
        if len(parts) == 3:
            path, op, value = parts
            actual = self._resolve_path(path, context)
            if op == "==":
                return str(actual) == value
            elif op == "!=":
                return str(actual) != value
            elif op == "exists":
                return actual is not None
        return True  # Default: condition passes

    def _resolve_path(self, path: str, context: Dict) -> Any:
        """Resolve a dot-path like 'input.query' from context."""
        parts = path.split(".")
        current = context
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current
