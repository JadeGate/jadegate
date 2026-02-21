"""
Test suite for JADE Validator.
Tests schema compliance, structural validation, and semantic checks.
"""

import json
import pytest
from pathlib import Path
from jade_core.validator import JadeValidator
from jade_core.models import ValidationSeverity
from tests.conftest import make_skill


class TestValidatorBasics:
    """Basic validator functionality."""

    def test_validate_minimal_skill(self, validator, minimal_skill_file):
        result = validator.validate_file(minimal_skill_file)
        assert result.valid, f"Errors: {[i.message for i in result.errors]}"

    def test_validate_nonexistent_file(self, validator):
        result = validator.validate_file("/nonexistent/path.json")
        assert not result.valid
        assert any(i.code == "FILE_NOT_FOUND" for i in result.issues)

    def test_validate_invalid_json(self, validator, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json content", encoding="utf-8")
        result = validator.validate_file(str(bad_file))
        assert not result.valid
        assert any(i.code == "INVALID_JSON" for i in result.issues)

    def test_validate_empty_json(self, validator, tmp_path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("{}", encoding="utf-8")
        result = validator.validate_file(str(empty_file))
        assert not result.valid

    def test_validate_dict(self, validator, minimal_skill_dict):
        result = validator.validate_dict(minimal_skill_dict)
        assert result.valid, f"Errors: {[i.message for i in result.errors]}"


class TestValidatorRequiredFields:
    """Test that missing required fields are caught."""

    @pytest.mark.parametrize("field", [
        "jade_version", "skill_id", "metadata", "trigger",
        "execution_dag", "security"
    ])
    def test_missing_required_field(self, validator, minimal_skill_dict, field):
        del minimal_skill_dict[field]
        result = validator.validate_dict(minimal_skill_dict)
        assert not result.valid
        assert any(i.code == "MISSING_FIELD" for i in result.errors)


class TestValidatorVersion:
    """Test version validation."""

    def test_valid_version(self, validator):
        skill = make_skill(jade_version="1.0.0")
        result = validator.validate_dict(skill)
        assert result.valid

    def test_invalid_version_format(self, validator):
        skill = make_skill(jade_version="2.0.0")
        result = validator.validate_dict(skill)
        assert not result.valid
        assert any(i.code == "UNSUPPORTED_VERSION" for i in result.errors)

    def test_nonsense_version(self, validator):
        skill = make_skill(jade_version="abc")
        result = validator.validate_dict(skill)
        assert not result.valid


class TestValidatorSkillId:
    """Test skill_id format validation."""

    def test_valid_skill_id(self, validator):
        skill = make_skill(skill_id="my_cool_skill_123")
        result = validator.validate_dict(skill)
        assert result.valid

    def test_skill_id_too_short(self, validator):
        skill = make_skill(skill_id="ab")
        result = validator.validate_dict(skill)
        assert not result.valid
        assert any(i.code == "INVALID_SKILL_ID" for i in result.errors)

    def test_skill_id_uppercase(self, validator):
        skill = make_skill(skill_id="MySkill")
        result = validator.validate_dict(skill)
        assert not result.valid

    def test_skill_id_starts_with_number(self, validator):
        skill = make_skill(skill_id="123skill")
        result = validator.validate_dict(skill)
        assert not result.valid

    def test_skill_id_with_spaces(self, validator):
        skill = make_skill(skill_id="my skill")
        result = validator.validate_dict(skill)
        assert not result.valid

    def test_skill_id_with_hyphens(self, validator):
        skill = make_skill(skill_id="my-skill")
        result = validator.validate_dict(skill)
        assert not result.valid


class TestValidatorMetadata:
    """Test metadata validation."""

    def test_missing_metadata_name(self, validator):
        skill = make_skill()
        del skill["metadata"]["name"]
        result = validator.validate_dict(skill)
        assert not result.valid

    def test_empty_tags(self, validator):
        skill = make_skill()
        skill["metadata"]["tags"] = []
        result = validator.validate_dict(skill)
        assert not result.valid

    def test_invalid_version_in_metadata(self, validator):
        skill = make_skill()
        skill["metadata"]["version"] = "not-a-version"
        result = validator.validate_dict(skill)
        assert not result.valid


class TestValidateGoldenSkills:
    """Validate all 5 golden skills pass validation."""

    def test_all_golden_skills_valid(self, validator, all_skill_files):
        assert len(all_skill_files) == 5, f"Expected 5 skills, got {len(all_skill_files)}"
        for skill_file in all_skill_files:
            result = validator.validate_file(skill_file)
            fname = Path(skill_file).name
            assert result.valid, (
                f"{fname} failed validation: "
                f"{[i.message for i in result.errors]}"
            )

    @pytest.mark.parametrize("skill_name", [
        "web_anti_crawl.json",
        "pdf_table_parser.json",
        "weather_api.json",
        "file_batch_rename.json",
        "email_send_safe.json",
    ])
    def test_individual_golden_skill(self, validator, skill_name):
        skill_path = Path(__file__).parent.parent / "jade_skills" / skill_name
        result = validator.validate_file(str(skill_path))
        assert result.valid, (
            f"{skill_name} failed: {[i.message for i in result.errors]}"
        )


class TestValidatorHashComputation:
    """Test that skill hashes are computed correctly."""

    def test_hash_is_deterministic(self, validator, minimal_skill_dict):
        result1 = validator.validate_dict(minimal_skill_dict)
        result2 = validator.validate_dict(minimal_skill_dict)
        assert result1.skill_hash == result2.skill_hash
        assert len(result1.skill_hash) == 64  # SHA-256

    def test_hash_changes_with_content(self, validator):
        skill1 = make_skill(skill_id="skill_aaa")
        skill2 = make_skill(skill_id="skill_bbb")
        r1 = validator.validate_dict(skill1)
        r2 = validator.validate_dict(skill2)
        assert r1.skill_hash != r2.skill_hash
