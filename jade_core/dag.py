"""
Project JADE - DAG (Directed Acyclic Graph) Engine
Validates and analyzes execution DAGs for structural correctness.

This module does NOT execute DAGs - it only validates their structure.
Execution is the responsibility of the local Agent runtime.
JADE only guarantees the DAG is safe and well-formed.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    DAGEdge,
    DAGNode,
    ExecutionDAG,
    JadeSkill,
    ValidationIssue,
    ValidationSeverity,
)


class DAGAnalyzer:
    """
    Analyzes and validates JADE execution DAGs.

    Checks:
    1. Structural integrity (all referenced nodes exist)
    2. Acyclicity (no cycles - it's a DAG after all)
    3. Reachability (all nodes reachable from entry)
    4. Exit reachability (at least one exit node reachable)
    5. No orphan nodes
    6. No duplicate node IDs
    7. Edge condition validity
    8. Entry/exit node validity
    """

    def validate(self, skill: JadeSkill) -> List[ValidationIssue]:
        """Run all DAG validation checks."""
        issues: List[ValidationIssue] = []
        dag = skill.execution_dag

        issues.extend(self._check_node_uniqueness(dag))
        issues.extend(self._check_entry_node(dag))
        issues.extend(self._check_exit_nodes(dag))
        issues.extend(self._check_edge_references(dag))
        issues.extend(self._check_acyclicity(dag))
        issues.extend(self._check_reachability(dag))
        issues.extend(self._check_exit_reachability(dag))
        issues.extend(self._check_edge_conditions(dag))
        issues.extend(self._check_orphan_nodes(dag))

        return issues

    def _check_node_uniqueness(self, dag: ExecutionDAG) -> List[ValidationIssue]:
        """Ensure all node IDs are unique."""
        issues: List[ValidationIssue] = []
        seen: Dict[str, int] = {}
        for i, node in enumerate(dag.nodes):
            if node.id in seen:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DAG_DUPLICATE_NODE",
                    message=f"Duplicate node ID '{node.id}' at index {i} "
                            f"(first seen at index {seen[node.id]})",
                    path=f"execution_dag.nodes[{i}].id",
                ))
            else:
                seen[node.id] = i
        return issues

    def _check_entry_node(self, dag: ExecutionDAG) -> List[ValidationIssue]:
        """Verify entry node exists in the node list."""
        issues: List[ValidationIssue] = []
        node_ids = {n.id for n in dag.nodes}
        if dag.entry_node not in node_ids:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="DAG_INVALID_ENTRY",
                message=f"Entry node '{dag.entry_node}' does not exist in nodes list",
                path="execution_dag.entry_node",
            ))
        return issues

    def _check_exit_nodes(self, dag: ExecutionDAG) -> List[ValidationIssue]:
        """Verify all exit nodes exist in the node list."""
        issues: List[ValidationIssue] = []
        node_ids = {n.id for n in dag.nodes}
        for exit_id in dag.exit_node:
            if exit_id not in node_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DAG_INVALID_EXIT",
                    message=f"Exit node '{exit_id}' does not exist in nodes list",
                    path="execution_dag.exit_node",
                ))
        if not dag.exit_node:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="DAG_NO_EXIT",
                message="DAG must have at least one exit node",
                path="execution_dag.exit_node",
            ))
        return issues

    def _check_edge_references(self, dag: ExecutionDAG) -> List[ValidationIssue]:
        """Verify all edges reference existing nodes."""
        issues: List[ValidationIssue] = []
        node_ids = {n.id for n in dag.nodes}
        for i, edge in enumerate(dag.edges):
            if edge.from_node not in node_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DAG_INVALID_EDGE_SRC",
                    message=f"Edge {i} references non-existent source node '{edge.from_node}'",
                    path=f"execution_dag.edges[{i}].from",
                ))
            if edge.to_node not in node_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DAG_INVALID_EDGE_DST",
                    message=f"Edge {i} references non-existent target node '{edge.to_node}'",
                    path=f"execution_dag.edges[{i}].to",
                ))
        return issues

    def _check_acyclicity(self, dag: ExecutionDAG) -> List[ValidationIssue]:
        """Detect cycles using DFS-based topological sort."""
        issues: List[ValidationIssue] = []

        # Build adjacency list
        adj: Dict[str, List[str]] = {n.id: [] for n in dag.nodes}
        for edge in dag.edges:
            if edge.from_node in adj:
                adj[edge.from_node].append(edge.to_node)

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {n.id: WHITE for n in dag.nodes}
        path: List[str] = []

        def dfs(node_id: str) -> bool:
            color[node_id] = GRAY
            path.append(node_id)
            for neighbor in adj.get(node_id, []):
                if color.get(neighbor) == GRAY:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="DAG_CYCLE_DETECTED",
                        message=f"Cycle detected: {' -> '.join(cycle)}",
                        path="execution_dag.edges",
                    ))
                    return True
                if color.get(neighbor) == WHITE:
                    if dfs(neighbor):
                        return True
            color[node_id] = BLACK
            path.pop()
            return False

        for node in dag.nodes:
            if color[node.id] == WHITE:
                dfs(node.id)

        return issues

    def _check_reachability(self, dag: ExecutionDAG) -> List[ValidationIssue]:
        """Ensure all nodes are reachable from the entry node."""
        issues: List[ValidationIssue] = []
        node_ids = {n.id for n in dag.nodes}

        if dag.entry_node not in node_ids:
            return issues  # Entry node check will catch this

        # BFS from entry
        reachable: Set[str] = set()
        queue = deque([dag.entry_node])
        adj: Dict[str, List[str]] = {n.id: [] for n in dag.nodes}
        for edge in dag.edges:
            if edge.from_node in adj:
                adj[edge.from_node].append(edge.to_node)

        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            for neighbor in adj.get(current, []):
                if neighbor not in reachable:
                    queue.append(neighbor)

        unreachable = node_ids - reachable
        for node_id in unreachable:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="DAG_UNREACHABLE_NODE",
                message=f"Node '{node_id}' is not reachable from entry node '{dag.entry_node}'",
                path=f"execution_dag.nodes",
            ))

        return issues

    def _check_exit_reachability(self, dag: ExecutionDAG) -> List[ValidationIssue]:
        """Ensure at least one exit node is reachable from entry."""
        issues: List[ValidationIssue] = []
        node_ids = {n.id for n in dag.nodes}

        if dag.entry_node not in node_ids:
            return issues

        # BFS from entry
        reachable: Set[str] = set()
        queue = deque([dag.entry_node])
        adj: Dict[str, List[str]] = {n.id: [] for n in dag.nodes}
        for edge in dag.edges:
            if edge.from_node in adj:
                adj[edge.from_node].append(edge.to_node)

        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            for neighbor in adj.get(current, []):
                if neighbor not in reachable:
                    queue.append(neighbor)

        reachable_exits = set(dag.exit_node) & reachable
        if not reachable_exits:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="DAG_NO_REACHABLE_EXIT",
                message="No exit node is reachable from the entry node",
                path="execution_dag",
            ))

        return issues

    def _check_edge_conditions(self, dag: ExecutionDAG) -> List[ValidationIssue]:
        """Validate edge conditions are well-formed."""
        issues: List[ValidationIssue] = []
        valid_conditions = {"success", "failure", None}

        for i, edge in enumerate(dag.edges):
            if edge.condition not in valid_conditions:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="DAG_INVALID_CONDITION",
                    message=f"Edge {i} has unknown condition '{edge.condition}'. "
                            f"Expected 'success', 'failure', or none.",
                    path=f"execution_dag.edges[{i}].condition",
                ))

        # Check that conditional edges come in pairs (success + failure)
        conditional_sources: Dict[str, List[str]] = {}
        for edge in dag.edges:
            if edge.condition:
                if edge.from_node not in conditional_sources:
                    conditional_sources[edge.from_node] = []
                conditional_sources[edge.from_node].append(edge.condition)

        for node_id, conditions in conditional_sources.items():
            cond_set = set(conditions)
            if cond_set == {"success"} or cond_set == {"failure"}:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="DAG_INCOMPLETE_BRANCH",
                    message=f"Node '{node_id}' has conditional edges but only "
                            f"covers {cond_set}. Consider adding the missing branch.",
                    path="execution_dag.edges",
                ))

        return issues

    def _check_orphan_nodes(self, dag: ExecutionDAG) -> List[ValidationIssue]:
        """Check for nodes with no incoming or outgoing edges (except entry/exit)."""
        issues: List[ValidationIssue] = []
        node_ids = {n.id for n in dag.nodes}
        has_incoming = {e.to_node for e in dag.edges}
        has_outgoing = {e.from_node for e in dag.edges}
        exit_set = set(dag.exit_node)

        for node_id in node_ids:
            if node_id == dag.entry_node:
                continue
            if node_id not in has_incoming:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="DAG_NO_INCOMING",
                    message=f"Non-entry node '{node_id}' has no incoming edges",
                    path="execution_dag.edges",
                ))
            if node_id not in has_outgoing and node_id not in exit_set:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="DAG_DEAD_END",
                    message=f"Non-exit node '{node_id}' has no outgoing edges (dead end)",
                    path="execution_dag.edges",
                ))

        return issues

    def get_topological_order(self, dag: ExecutionDAG) -> List[str]:
        """Return nodes in topological order. Returns empty list if cycle exists."""
        in_degree: Dict[str, int] = {n.id: 0 for n in dag.nodes}
        adj: Dict[str, List[str]] = {n.id: [] for n in dag.nodes}

        for edge in dag.edges:
            if edge.to_node in in_degree:
                in_degree[edge.to_node] += 1
            if edge.from_node in adj:
                adj[edge.from_node].append(edge.to_node)

        queue = deque([n for n, d in in_degree.items() if d == 0])
        order: List[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in adj.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(dag.nodes):
            return []  # Cycle exists
        return order

    def get_execution_paths(self, dag: ExecutionDAG) -> List[List[str]]:
        """Enumerate all possible execution paths from entry to exit nodes."""
        paths: List[List[str]] = []
        exit_set = set(dag.exit_node)
        adj: Dict[str, List[Tuple[str, Optional[str]]]] = {n.id: [] for n in dag.nodes}
        for edge in dag.edges:
            if edge.from_node in adj:
                adj[edge.from_node].append((edge.to_node, edge.condition))

        def dfs(current: str, path: List[str], visited: Set[str]) -> None:
            if current in exit_set:
                paths.append(list(path))
                return
            if current in visited:
                return
            visited.add(current)
            for neighbor, _ in adj.get(current, []):
                path.append(neighbor)
                dfs(neighbor, path, visited)
                path.pop()
            visited.discard(current)

        dfs(dag.entry_node, [dag.entry_node], set())
        return paths

    def compute_max_depth(self, dag: ExecutionDAG) -> int:
        """Compute the maximum depth (longest path) of the DAG."""
        topo = self.get_topological_order(dag)
        if not topo:
            return -1  # Cycle

        adj: Dict[str, List[str]] = {n.id: [] for n in dag.nodes}
        for edge in dag.edges:
            if edge.from_node in adj:
                adj[edge.from_node].append(edge.to_node)

        dist: Dict[str, int] = {n: 0 for n in topo}
        for node_id in topo:
            for neighbor in adj.get(node_id, []):
                if dist[neighbor] < dist[node_id] + 1:
                    dist[neighbor] = dist[node_id] + 1

        return max(dist.values()) if dist else 0
