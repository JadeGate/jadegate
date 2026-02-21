"""
Test suite for JADE Client SDK.
Tests local loading, validation, caching, and skill info.
"""

import json
import os
import pytest
from pathlib import Path
from jade_core.client import JadeClient
from jade_core.models import JadeSkill, ValidationSeverity
from tests.conftest import make_skill


class TestClientLoadFile:
    """Test loading skills from local files."""

    def test_load_valid_skill(self, client, minimal_skill_file):
        skill, result = client.load_file(minimal_skill_file)
        assert skill is not None
        assert result.valid
        assert skill.skill_id == "test_skill"

    def test_load_invalid_file(self, client, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{}", encoding="utf-8")
        skill, result = client.load_file(str(bad_file))
        assert skill is None
        assert not result.valid

    def test_load_nonexistent_file(self, client):
        skill, result = client.load_file("/nonexistent/file.json")
        assert skill is None
        assert not result.valid

    def test_load_without_validation(self, client, minimal_skill_file):
        # Create client with auto_validate=False
        from jade_core.client import JadeClient
        from jade_core.validator import JadeValidator
        from jade_core.registry import JadeRegistry
        c = JadeClient(
            cache_dir=str(client.cache_dir),
            validator=JadeValidator(),
            registry=JadeRegistry(),
            auto_validate=False,
        )
        skill, result = c.load_file(minimal_skill_file, validate=False)
        assert skill is not None
        assert result.valid  # No validation performed


class TestClientLoadDirectory:
    """Test loading all skills from a directory."""

    def test_load_all_golden_skills(self, client, tmp_skills_dir):
        results = client.load_directory(tmp_skills_dir)
        assert len(results) == 5
        for fname, (skill, result) in results.items():
            assert skill is not None, f"{fname} failed to load: {[i.message for i in result.errors]}"
            assert result.valid, f"{fname} invalid: {[i.message for i in result.errors]}"

    def test_load_empty_directory(self, client, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        results = client.load_directory(str(empty_dir))
        assert len(results) == 0

    def test_load_mixed_directory(self, client, tmp_path):
        """Directory with valid and invalid skills."""
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()

        # Valid skill
        valid = make_skill(skill_id="valid_skill")
        (mixed_dir / "valid.json").write_text(json.dumps(valid), encoding="utf-8")

        # Invalid skill (missing required fields)
        (mixed_dir / "invalid.json").write_text(json.dumps({"bad": True}), encoding="utf-8")

        results = client.load_directory(str(mixed_dir))
        assert len(results) == 2

        valid_skill, valid_result = results["valid.json"]
        assert valid_skill is not None
        assert valid_result.valid

        invalid_skill, invalid_result = results["invalid.json"]
        assert invalid_skill is None
        assert not invalid_result.valid


class TestClientLoadedSkills:
    """Test loaded skill management."""

    def test_get_loaded_skill(self, client, minimal_skill_file):
        client.load_file(minimal_skill_file)
        skill = client.get_loaded_skill("test_skill")
        assert skill is not None
        assert skill.skill_id == "test_skill"

    def test_get_nonexistent_loaded_skill(self, client):
        skill = client.get_loaded_skill("ghost")
        assert skill is None

    def test_loaded_skills_dict(self, client, minimal_skill_file):
        client.load_file(minimal_skill_file)
        loaded = client.loaded_skills
        assert "test_skill" in loaded
        assert len(loaded) == 1


class TestClientSkillInfo:
    """Test skill info and export."""

    def test_get_skill_info(self, client, minimal_skill_file):
        client.load_file(minimal_skill_file)
        info = client.get_skill_info("test_skill")
        assert info is not None
        assert info["skill_id"] == "test_skill"
        assert info["name"] == "Test Skill"
        assert info["version"] == "1.0.0"
        assert "hash" in info

    def test_get_info_nonexistent(self, client):
        info = client.get_skill_info("ghost")
        assert info is None

    def test_export_skill_list(self, client, tmp_skills_dir):
        client.load_directory(tmp_skills_dir)
        skill_list = client.export_skill_list()
        assert len(skill_list) == 5
        # Should be sorted by skill_id
        ids = [s["skill_id"] for s in skill_list]
        assert ids == sorted(ids)


class TestClientCache:
    """Test local caching."""

    def test_cache_dir_created(self, client):
        assert client.cache_dir.exists()

    def test_clear_cache(self, client, tmp_path):
        # Put something in cache
        cache_file = client.cache_dir / "test.json"
        cache_file.write_text("{}", encoding="utf-8")
        assert cache_file.exists()
        client.clear_cache()
        # Cache dir should still exist but be empty
        assert client.cache_dir.exists()


class TestClientTriggerMatch:
    """Test trigger matching for skill discovery."""

    def test_find_skill_by_trigger(self, client, tmp_skills_dir):
        client.load_directory(tmp_skills_dir)

        # Weather skill should match task_intent "get_weather"
        matches = client.find_skills_by_trigger(
            trigger_type="task_intent",
            context={"task.type": "get_weather"},
        )
        assert len(matches) > 0
        assert any(s.skill_id == "weather_api_query" for s in matches)

    def test_no_match_returns_empty(self, client, tmp_skills_dir):
        client.load_directory(tmp_skills_dir)
        matches = client.find_skills_by_trigger(
            trigger_type="task_intent",
            context={"task.type": "fly_to_moon"},
        )
        assert len(matches) == 0


class TestClientAttestation:
    """Test attestation submission through client."""

    def test_submit_attestation_success(self, client, minimal_skill_file):
        client.load_file(minimal_skill_file)
        # Register in registry first
        skill = client.get_loaded_skill("test_skill")
        client._registry.register(skill)

        result = client.submit_attestation(
            skill_id="test_skill",
            success=True,
            execution_time_ms=150,
        )
        assert result is True

    def test_submit_attestation_for_unknown_skill(self, client):
        result = client.submit_attestation(
            skill_id="ghost_skill",
            success=True,
            execution_time_ms=100,
        )
        assert result is False
