"""
Test suite for JADE Registry.
Tests registration, Bayesian confidence scoring, time decay, attestations.
"""

import json
import math
import time
import pytest
from jade_core.registry import JadeRegistry, PRIOR_ALPHA, PRIOR_BETA
from jade_core.models import (
    JadeSkill,
    Attestation,
    AttestationType,
    RegistryEntry,
)
from tests.conftest import make_skill


class TestRegistration:
    """Test skill registration."""

    def test_register_new_skill(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        entry = registry.register(skill)
        assert entry.skill_id == "test_skill"
        assert entry.confidence_score == 0.5  # Laplace prior
        assert entry.success_count == 0
        assert entry.failure_count == 0
        assert registry.size == 1

    def test_register_duplicate_same_hash(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        entry1 = registry.register(skill)
        entry2 = registry.register(skill)
        assert entry1.skill_hash == entry2.skill_hash
        assert registry.size == 1

    def test_register_updated_skill(self, registry):
        skill1 = JadeSkill.from_dict(make_skill())
        registry.register(skill1)

        skill_dict2 = make_skill()
        skill_dict2["metadata"]["version"] = "2.0.0"
        skill2 = JadeSkill.from_dict(skill_dict2)
        entry2 = registry.register(skill2)
        assert entry2.success_count == 0  # Reset on new version
        assert registry.size == 1

    def test_unregister_skill(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        registry.register(skill)
        assert registry.unregister("test_skill") is True
        assert registry.size == 0

    def test_unregister_nonexistent(self, registry):
        assert registry.unregister("ghost_skill") is False

    def test_register_multiple_skills(self, registry):
        for i in range(5):
            skill_dict = make_skill(skill_id=f"skill_{i:03d}")
            skill = JadeSkill.from_dict(skill_dict)
            registry.register(skill)
        assert registry.size == 5


class TestBayesianConfidence:
    """Test Bayesian confidence scoring."""

    def test_initial_confidence_is_half(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        entry = registry.register(skill)
        # (0 + 1) / (0 + 0 + 1 + 1) = 0.5
        assert entry.confidence_score == pytest.approx(0.5)

    def test_confidence_increases_with_success(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        registry.register(skill)
        entry = None

        for i in range(10):
            att = Attestation(
                skill_id="test_skill",
                skill_hash=skill.compute_hash(),
                success=True,
                execution_time_ms=100,
            )
            entry = registry.submit_attestation(att)

        # (10 + 1) / (10 + 0 + 1 + 1) = 11/12 ≈ 0.917
        expected = (10 + PRIOR_ALPHA) / (10 + 0 + PRIOR_ALPHA + PRIOR_BETA)
        assert entry is not None
        assert entry.confidence_score == pytest.approx(expected)
        assert entry.confidence_score > 0.9

    def test_confidence_decreases_with_failure(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        registry.register(skill)
        entry = None

        for i in range(10):
            att = Attestation(
                skill_id="test_skill",
                skill_hash=skill.compute_hash(),
                success=False,
                execution_time_ms=100,
            )
            entry = registry.submit_attestation(att)

        # (0 + 1) / (0 + 10 + 1 + 1) = 1/12 ≈ 0.083
        expected = (0 + PRIOR_ALPHA) / (0 + 10 + PRIOR_ALPHA + PRIOR_BETA)
        assert entry is not None
        assert entry.confidence_score == pytest.approx(expected)
        assert entry.confidence_score < 0.1

    def test_mixed_attestations(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        registry.register(skill)
        skill_hash = skill.compute_hash()

        # 80 successes, 20 failures
        for i in range(80):
            registry.submit_attestation(Attestation(
                skill_id="test_skill", skill_hash=skill_hash,
                success=True, execution_time_ms=100,
            ))
        for i in range(20):
            registry.submit_attestation(Attestation(
                skill_id="test_skill", skill_hash=skill_hash,
                success=False, execution_time_ms=100,
            ))

        entry = registry.entries["test_skill"]
        # (80 + 1) / (80 + 20 + 1 + 1) = 81/102 ≈ 0.794
        expected = (80 + PRIOR_ALPHA) / (80 + 20 + PRIOR_ALPHA + PRIOR_BETA)
        assert entry.confidence_score == pytest.approx(expected)

    def test_attestation_for_nonexistent_skill_raises(self, registry):
        att = Attestation(
            skill_id="ghost_skill",
            skill_hash="abc",
            success=True,
            execution_time_ms=100,
        )
        with pytest.raises(ValueError, match="not found"):
            registry.submit_attestation(att)

    def test_hash_mismatch_raises(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        registry.register(skill)
        att = Attestation(
            skill_id="test_skill",
            skill_hash="wrong_hash_value",
            success=True,
            execution_time_ms=100,
        )
        with pytest.raises(ValueError, match="mismatch"):
            registry.submit_attestation(att)


class TestTimeDecay:
    """Test confidence time decay."""

    def test_decay_reduces_confidence(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        registry.register(skill)
        skill_hash = skill.compute_hash()

        # Add some successes
        for _ in range(10):
            registry.submit_attestation(Attestation(
                skill_id="test_skill", skill_hash=skill_hash,
                success=True, execution_time_ms=100,
            ))

        before = registry.entries["test_skill"].confidence_score
        registry.apply_time_decay(days_elapsed=30)
        after = registry.entries["test_skill"].confidence_score
        assert after < before

    def test_zero_decay_no_change(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        entry = registry.register(skill)
        original = entry.confidence_score
        registry.apply_time_decay(days_elapsed=0)
        assert registry.entries["test_skill"].confidence_score == pytest.approx(original)


class TestPersistence:
    """Test save/load to JSON."""

    def test_save_and_load(self, registry, tmp_path):
        # Register skills
        for i in range(3):
            skill = JadeSkill.from_dict(make_skill(skill_id=f"skill_{i:03d}"))
            registry.register(skill)

        # Save
        save_path = str(tmp_path / "test_index.json")
        registry.save(save_path)

        # Load into new registry
        new_registry = JadeRegistry(index_path=save_path)
        assert new_registry.size == 3
        assert "skill_000" in new_registry.entries
        assert "skill_001" in new_registry.entries
        assert "skill_002" in new_registry.entries

    def test_save_empty_registry(self, registry, tmp_path):
        save_path = str(tmp_path / "empty_index.json")
        registry.save(save_path)
        new_registry = JadeRegistry(index_path=save_path)
        assert new_registry.size == 0


class TestRegistrySearch:
    """Test skill search functionality."""

    def test_get_top_skills(self, registry):
        # Register skills with different confidence
        for i in range(5):
            skill = JadeSkill.from_dict(make_skill(skill_id=f"skill_{i:03d}"))
            registry.register(skill)
            skill_hash = skill.compute_hash()
            for _ in range(i * 10):
                registry.submit_attestation(Attestation(
                    skill_id=f"skill_{i:03d}", skill_hash=skill_hash,
                    success=True, execution_time_ms=100,
                ))

        top = registry.get_top_skills(limit=3)
        assert len(top) == 3
        # Should be sorted by confidence descending
        assert top[0].confidence_score >= top[1].confidence_score
        assert top[1].confidence_score >= top[2].confidence_score

    def test_get_entry(self, registry):
        skill = JadeSkill.from_dict(make_skill())
        registry.register(skill)
        entry = registry.get_entry("test_skill")
        assert entry is not None
        assert entry.skill_id == "test_skill"

    def test_get_nonexistent_entry(self, registry):
        entry = registry.get_entry("ghost")
        assert entry is None
