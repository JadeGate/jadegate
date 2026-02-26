"""
End-to-end integration tests for Project JADE.
Tests the full workflow: load -> validate -> register -> attest -> query.
"""

import json
import os
import pytest
from pathlib import Path
from jade_core.validator import JadeValidator
from jade_core.security import SecurityEngine
from jade_core.dag import DAGAnalyzer
from jade_core.client import JadeClient
from jade_core.registry import JadeRegistry
from jade_core.models import (
    JadeSkill,
    Attestation,
    AttestationType,
    ValidationSeverity,
)
from tests.conftest import make_skill


class TestFullWorkflow:
    """Test the complete JADE workflow end-to-end."""

    def test_load_validate_register_attest(self, tmp_path):
        """Full lifecycle: create skill -> validate -> register -> attest -> query."""
        # 1. Create a skill file
        skill_dict = make_skill(skill_id="e2e_test_skill")
        skill_file = tmp_path / "e2e_skill.json"
        skill_file.write_text(json.dumps(skill_dict, indent=2), encoding="utf-8")

        # 2. Create components
        validator = JadeValidator()
        registry = JadeRegistry()
        client = JadeClient(
            cache_dir=str(tmp_path / "cache"),
            validator=validator,
            registry=registry,
        )

        # 3. Load and validate
        skill, result = client.load_file(str(skill_file))
        assert skill is not None, f"Load failed: {[i.message for i in result.errors]}"
        assert result.valid

        # 4. Register
        entry = registry.register(skill)
        assert entry.skill_id == "e2e_test_skill"
        assert entry.confidence_score == pytest.approx(0.5)

        # 5. Submit attestations
        skill_hash = skill.compute_hash()
        for _ in range(10):
            registry.submit_attestation(Attestation(
                skill_id="e2e_test_skill",
                skill_hash=skill_hash,
                success=True,
                execution_time_ms=50,
            ))

        # 6. Verify confidence increased
        entry = registry.get_entry("e2e_test_skill")
        assert entry.confidence_score > 0.8
        assert entry.success_count == 10

        # 7. Save and reload registry
        index_path = str(tmp_path / "index.json")
        registry.save(index_path)
        new_registry = JadeRegistry(index_path=index_path)
        assert new_registry.size == 1
        reloaded = new_registry.get_entry("e2e_test_skill")
        assert reloaded.success_count == 10


class TestGoldenSkillsE2E:
    """End-to-end tests with all 5 golden skills."""

    def test_load_all_validate_register(self, tmp_path):
        """Load all golden skills, validate, register, and verify."""
        skills_dir = Path(__file__).parent.parent / "jade_skills"
        validator = JadeValidator()
        registry = JadeRegistry()
        client = JadeClient(
            cache_dir=str(tmp_path / "cache"),
            validator=validator,
            registry=registry,
        )

        # Load all skills
        results = client.load_directory(str(skills_dir))
        assert len(results) == 5

        # All should be valid
        for fname, (skill, result) in results.items():
            assert skill is not None, f"{fname} load failed"
            assert result.valid, f"{fname} invalid: {[i.message for i in result.errors]}"

            # Register each
            entry = registry.register(skill)
            assert entry.skill_id == skill.skill_id

        assert registry.size == 5

        # Simulate attestations for each
        for skill_id, entry in registry.entries.items():
            skill = client.get_loaded_skill(skill_id)
            skill_hash = skill.compute_hash()
            for _ in range(20):
                registry.submit_attestation(Attestation(
                    skill_id=skill_id,
                    skill_hash=skill_hash,
                    success=True,
                    execution_time_ms=100,
                ))

        # All should have high confidence
        for entry in registry.entries.values():
            assert entry.confidence_score > 0.9
            assert entry.success_count == 20

    def test_golden_skills_security_clean(self, tmp_path):
        """Verify all golden skills pass deep security scan."""
        skills_dir = Path(__file__).parent.parent / "jade_skills"
        validator = JadeValidator()

        for skill_file in sorted(skills_dir.glob("*.json")):
            result = validator.validate_file(str(skill_file))
            sec_issues = [
                i for i in result.issues
                if i.code.startswith("SEC_") and i.severity == ValidationSeverity.ERROR
            ]
            assert len(sec_issues) == 0, (
                f"{skill_file.name} has security issues: "
                f"{[(i.code, i.message) for i in sec_issues]}"
            )


class TestMaliciousSkillRejection:
    """Test that various attack vectors are properly rejected."""

    def test_reject_code_injection(self, tmp_path):
        """Skill with executable code should be rejected."""
        skill_dict = make_skill(skill_id="evil_skill")
        skill_dict["execution_dag"]["nodes"][0]["params"]["input"] = "eval('__import__(\"os\").system(\"rm -rf /\")')"

        skill_file = tmp_path / "evil.json"
        skill_file.write_text(json.dumps(skill_dict), encoding="utf-8")

        validator = JadeValidator()
        result = validator.validate_file(str(skill_file))
        assert not result.valid
        assert any(i.code.startswith("SEC_") for i in result.errors)

    def test_reject_network_exfiltration(self, tmp_path):
        """Skill trying to access suspicious networks should be flagged."""
        skill_dict = make_skill(skill_id="exfil_skill")
        skill_dict["security"]["network_whitelist"] = ["192.168.1.1"]
        skill_dict["security"]["sandbox_level"] = "strict"

        skill_file = tmp_path / "exfil.json"
        skill_file.write_text(json.dumps(skill_dict), encoding="utf-8")

        validator = JadeValidator()
        result = validator.validate_file(str(skill_file))
        assert not result.valid

    def test_reject_cyclic_dag(self, tmp_path):
        """Skill with cyclic DAG should be rejected."""
        skill_dict = make_skill(skill_id="cyclic_skill")
        skill_dict["execution_dag"]["nodes"] = [
            {"id": "node_a", "action": "json_parse", "params": {}},
            {"id": "node_b", "action": "json_parse", "params": {}},
        ]
        skill_dict["execution_dag"]["edges"] = [
            {"from": "node_a", "to": "node_b"},
            {"from": "node_b", "to": "node_a"},
        ]
        skill_dict["execution_dag"]["entry_node"] = "node_a"
        skill_dict["execution_dag"]["exit_node"] = ["node_b"]

        skill_file = tmp_path / "cyclic.json"
        skill_file.write_text(json.dumps(skill_dict), encoding="utf-8")

        validator = JadeValidator()
        result = validator.validate_file(str(skill_file))
        assert not result.valid
        assert any(i.code == "DAG_CYCLE_DETECTED" for i in result.issues)

    def test_reject_dangerous_commands(self, tmp_path):
        """Skill with dangerous system commands should be rejected."""
        skill_dict = make_skill(skill_id="danger_skill")
        skill_dict["execution_dag"]["nodes"][0]["params"]["input"] = "sudo rm -rf /"

        skill_file = tmp_path / "danger.json"
        skill_file.write_text(json.dumps(skill_dict), encoding="utf-8")

        validator = JadeValidator()
        result = validator.validate_file(str(skill_file))
        assert not result.valid


class TestRegistryPersistenceE2E:
    """Test registry save/load with real data."""

    def test_full_registry_persistence(self, tmp_path):
        """Register, attest, save, load, verify all data intact."""
        registry = JadeRegistry()

        # Register 3 skills with different attestation profiles
        profiles = [
            ("skill_good", 50, 2),    # High confidence
            ("skill_mid", 30, 15),     # Medium confidence
            ("skill_bad", 5, 40),      # Low confidence
        ]

        for skill_id, successes, failures in profiles:
            skill = JadeSkill.from_dict(make_skill(skill_id=skill_id))
            registry.register(skill)
            skill_hash = skill.compute_hash()

            for _ in range(successes):
                registry.submit_attestation(Attestation(
                    skill_id=skill_id, skill_hash=skill_hash,
                    success=True, execution_time_ms=100,
                ))
            for _ in range(failures):
                registry.submit_attestation(Attestation(
                    skill_id=skill_id, skill_hash=skill_hash,
                    success=False, execution_time_ms=100,
                ))

        # Save
        index_path = str(tmp_path / "full_index.json")
        registry.save(index_path)

        # Load
        loaded = JadeRegistry(index_path=index_path)
        assert loaded.size == 3

        # Verify ordering
        top = loaded.get_top_skills(limit=3)
        assert top[0].skill_id == "skill_good"
        assert top[2].skill_id == "skill_bad"

        # Verify counts preserved
        good = loaded.get_entry("skill_good")
        assert good.success_count == 50
        assert good.failure_count == 2


class TestHashDeterminism:
    """Test that skill hashes are deterministic and collision-resistant."""

    def test_same_skill_same_hash(self):
        skill1 = JadeSkill.from_dict(make_skill())
        skill2 = JadeSkill.from_dict(make_skill())
        assert skill1.compute_hash() == skill2.compute_hash()

    def test_different_skills_different_hash(self):
        skill1 = JadeSkill.from_dict(make_skill(skill_id="skill_aaa"))
        skill2 = JadeSkill.from_dict(make_skill(skill_id="skill_bbb"))
        assert skill1.compute_hash() != skill2.compute_hash()

    def test_hash_changes_with_dag_modification(self):
        dict1 = make_skill()
        dict2 = make_skill()
        dict2["execution_dag"]["nodes"][0]["action"] = "regex_match"
        skill1 = JadeSkill.from_dict(dict1)
        skill2 = JadeSkill.from_dict(dict2)
        assert skill1.compute_hash() != skill2.compute_hash()

    def test_hash_is_sha256(self):
        skill = JadeSkill.from_dict(make_skill())
        h = skill.compute_hash()
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)
