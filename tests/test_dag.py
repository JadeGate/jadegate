"""
Test suite for JADE DAG Analyzer.
Tests structural integrity, acyclicity, reachability, etc.
"""

import pytest
from jade_core.dag import DAGAnalyzer
from jade_core.models import JadeSkill, ValidationSeverity
from tests.conftest import make_skill


class TestDAGNodeUniqueness:
    """Test duplicate node detection."""

    def test_duplicate_node_ids(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["nodes"].append({
            "id": "step_one",  # duplicate
            "action": "json_parse",
            "params": {"input": "test"},
        })
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(i.code == "DAG_DUPLICATE_NODE" for i in issues)

    def test_unique_nodes_pass(self, dag_analyzer, minimal_skill_dict):
        skill = JadeSkill.from_dict(minimal_skill_dict)
        issues = dag_analyzer.validate(skill)
        dup_issues = [i for i in issues if i.code == "DAG_DUPLICATE_NODE"]
        assert len(dup_issues) == 0


class TestDAGEntryExit:
    """Test entry and exit node validation."""

    def test_invalid_entry_node(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["entry_node"] = "nonexistent_node"
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(i.code == "DAG_INVALID_ENTRY" for i in issues)

    def test_invalid_exit_node(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["exit_node"] = ["nonexistent_exit"]
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(i.code == "DAG_INVALID_EXIT" for i in issues)

    def test_empty_exit_nodes(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["exit_node"] = []
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(i.code == "DAG_NO_EXIT" for i in issues)


class TestDAGEdgeReferences:
    """Test edge reference validation."""

    def test_edge_references_nonexistent_source(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["edges"] = [
            {"from": "ghost_node", "to": "step_two"}
        ]
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(i.code == "DAG_INVALID_EDGE_SRC" for i in issues)

    def test_edge_references_nonexistent_target(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["edges"] = [
            {"from": "step_one", "to": "ghost_node"}
        ]
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(i.code == "DAG_INVALID_EDGE_DST" for i in issues)


class TestDAGAcyclicity:
    """Test cycle detection."""

    def test_simple_cycle_detected(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["nodes"] = [
            {"id": "node_a", "action": "json_parse", "params": {}},
            {"id": "node_b", "action": "json_parse", "params": {}},
            {"id": "node_c", "action": "return_result", "params": {}},
        ]
        skill_dict["execution_dag"]["edges"] = [
            {"from": "node_a", "to": "node_b"},
            {"from": "node_b", "to": "node_a"},  # cycle!
            {"from": "node_b", "to": "node_c"},
        ]
        skill_dict["execution_dag"]["entry_node"] = "node_a"
        skill_dict["execution_dag"]["exit_node"] = ["node_c"]
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(i.code == "DAG_CYCLE_DETECTED" for i in issues)

    def test_self_loop_detected(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["edges"].append(
            {"from": "step_one", "to": "step_one"}  # self-loop
        )
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(i.code == "DAG_CYCLE_DETECTED" for i in issues)

    def test_acyclic_graph_passes(self, dag_analyzer, minimal_skill_dict):
        skill = JadeSkill.from_dict(minimal_skill_dict)
        issues = dag_analyzer.validate(skill)
        cycle_issues = [i for i in issues if i.code == "DAG_CYCLE_DETECTED"]
        assert len(cycle_issues) == 0


class TestDAGReachability:
    """Test node reachability from entry."""

    def test_unreachable_node_detected(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["nodes"].append({
            "id": "orphan_node",
            "action": "json_parse",
            "params": {},
        })
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(
            i.code in ("DAG_UNREACHABLE_NODE", "DAG_ORPHAN_NODE")
            for i in issues
        )

    def test_all_nodes_reachable(self, dag_analyzer, minimal_skill_dict):
        skill = JadeSkill.from_dict(minimal_skill_dict)
        issues = dag_analyzer.validate(skill)
        reach_issues = [i for i in issues if i.code == "DAG_UNREACHABLE_NODE"]
        assert len(reach_issues) == 0


class TestDAGEdgeConditions:
    """Test edge condition validation."""

    def test_valid_conditions(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["nodes"] = [
            {"id": "check", "action": "condition_check", "params": {"field": "x", "operator": "equals", "value": 1}},
            {"id": "on_success", "action": "return_result", "params": {"result": "ok"}},
            {"id": "on_failure", "action": "return_error", "params": {"error_code": "FAIL", "message": "failed"}},
        ]
        skill_dict["execution_dag"]["edges"] = [
            {"from": "check", "to": "on_success", "condition": "success"},
            {"from": "check", "to": "on_failure", "condition": "failure"},
        ]
        skill_dict["execution_dag"]["entry_node"] = "check"
        skill_dict["execution_dag"]["exit_node"] = ["on_success", "on_failure"]
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        cond_issues = [i for i in issues if i.code == "DAG_INVALID_CONDITION"]
        assert len(cond_issues) == 0

    def test_invalid_condition_value(self, dag_analyzer):
        skill_dict = make_skill()
        skill_dict["execution_dag"]["edges"] = [
            {"from": "step_one", "to": "step_two", "condition": "maybe"}
        ]
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        assert any(i.code == "DAG_INVALID_CONDITION" for i in issues)


class TestDAGComplexGraphs:
    """Test with more complex DAG structures."""

    def test_diamond_dag(self, dag_analyzer):
        """Diamond shape: A -> B, A -> C, B -> D, C -> D"""
        skill_dict = make_skill()
        skill_dict["execution_dag"] = {
            "nodes": [
                {"id": "start", "action": "json_parse", "params": {}},
                {"id": "branch_a", "action": "json_extract", "params": {"data": {}, "path": "$.a"}},
                {"id": "branch_b", "action": "json_extract", "params": {"data": {}, "path": "$.b"}},
                {"id": "merge", "action": "return_result", "params": {"result": "done"}},
            ],
            "edges": [
                {"from": "start", "to": "branch_a"},
                {"from": "start", "to": "branch_b"},
                {"from": "branch_a", "to": "merge"},
                {"from": "branch_b", "to": "merge"},
            ],
            "entry_node": "start",
            "exit_node": ["merge"],
        }
        skill = JadeSkill.from_dict(skill_dict)
        issues = dag_analyzer.validate(skill)
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_golden_skills_dag_valid(self, dag_analyzer, all_skill_files):
        """All golden skills should have valid DAGs."""
        import json as json_mod
        for skill_file in all_skill_files:
            with open(skill_file, "r") as f:
                data = json_mod.load(f)
            skill = JadeSkill.from_dict(data)
            issues = dag_analyzer.validate(skill)
            errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
            fname = skill_file.split("/")[-1]
            assert len(errors) == 0, f"{fname} DAG errors: {[i.message for i in errors]}"
