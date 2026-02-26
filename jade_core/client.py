"""
Project JADE - Client SDK
The agent-facing interface for fetching, verifying, and loading JADE skills.

Usage:
    client = JadeClient()
    skill = client.fetch("weather_api_query")
    if skill:
        print(skill.execution_dag.entry_node)

    # Or from local file
    skill = client.load_file("path/to/skill.json")
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from .models import (
    JadeSkill,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    RegistryEntry,
    Attestation,
    AttestationType,
)
from .validator import JadeValidator
from .registry import JadeRegistry


# Default GitHub raw content base URL
DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/project-jade/jade-registry/main"
DEFAULT_SKILLS_URL = "https://raw.githubusercontent.com/project-jade/jade-skills/main"


class JadeClient:
    """
    JADE Client SDK - The agent's interface to the JADE ecosystem.

    Features:
    1. Fetch skills from remote registry (GitHub-based)
    2. Load and validate local skill files
    3. Local skill cache management
    4. Attestation submission (success/failure reporting)
    5. Skill search by trigger conditions
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        registry_url: str = DEFAULT_REGISTRY_URL,
        skills_url: str = DEFAULT_SKILLS_URL,
        validator: Optional[JadeValidator] = None,
        registry: Optional[JadeRegistry] = None,
        auto_validate: bool = True,
    ):
        self._cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".jade" / "cache"
        self._registry_url = registry_url
        self._skills_url = skills_url
        self._validator = validator or JadeValidator()
        self._registry = registry or JadeRegistry()
        self._auto_validate = auto_validate
        self._loaded_skills: Dict[str, JadeSkill] = {}

        # Ensure cache directory exists
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    @property
    def loaded_skills(self) -> Dict[str, JadeSkill]:
        return dict(self._loaded_skills)

    # ─── Local Operations ───────────────────────────────────────────

    def load_file(self, file_path: str, validate: bool = True) -> Tuple[Optional[JadeSkill], ValidationResult]:
        """
        Load a JADE skill from a local JSON file.

        Returns:
            Tuple of (skill_or_none, validation_result)
        """
        if validate or self._auto_validate:
            result = self._validator.validate_file(file_path)
            if not result.valid:
                return None, result
        else:
            result = ValidationResult(valid=True)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        skill = JadeSkill.from_dict(data)
        self._loaded_skills[skill.skill_id] = skill
        return skill, result

    def load_directory(self, dir_path: str, validate: bool = True) -> Dict[str, Tuple[Optional[JadeSkill], ValidationResult]]:
        """Load all JADE skill files from a directory."""
        results: Dict[str, Tuple[Optional[JadeSkill], ValidationResult]] = {}
        dir_p = Path(dir_path)

        for json_file in sorted(dir_p.glob("*.json")):
            skill, result = self.load_file(str(json_file), validate=validate)
            results[json_file.name] = (skill, result)

        return results

    def get_loaded_skill(self, skill_id: str) -> Optional[JadeSkill]:
        """Get a previously loaded skill by ID."""
        return self._loaded_skills.get(skill_id)

    # ─── Remote Operations ──────────────────────────────────────────

    def fetch(self, skill_id: str, validate: bool = True) -> Tuple[Optional[JadeSkill], ValidationResult]:
        """
        Fetch a skill from the remote registry.

        1. Check local cache first
        2. If not cached, download from GitHub
        3. Validate before returning
        """
        # Check cache
        cached = self._load_from_cache(skill_id)
        if cached:
            if validate or self._auto_validate:
                result = self._validator.validate_dict(cached)
                if result.valid:
                    skill = JadeSkill.from_dict(cached)
                    self._loaded_skills[skill_id] = skill
                    return skill, result
                # Cache is invalid, re-fetch
            else:
                skill = JadeSkill.from_dict(cached)
                self._loaded_skills[skill_id] = skill
                return skill, ValidationResult(valid=True)

        # Download from remote
        try:
            data = self._download_skill(skill_id)
        except Exception as e:
            return None, ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="FETCH_FAILED",
                    message=f"Failed to fetch skill '{skill_id}': {e}",
                )],
            )

        if data is None:
            return None, ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="SKILL_NOT_FOUND",
                    message=f"Skill '{skill_id}' not found in remote registry",
                )],
            )

        # Validate
        if validate or self._auto_validate:
            result = self._validator.validate_dict(data)
            if not result.valid:
                return None, result
        else:
            result = ValidationResult(valid=True)

        # Cache locally
        self._save_to_cache(skill_id, data)

        skill = JadeSkill.from_dict(data)
        self._loaded_skills[skill_id] = skill
        return skill, result

    def _download_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Download a skill JSON from the remote skills repository."""
        url = f"{self._skills_url}/{skill_id}.json"
        try:
            req = Request(url, headers={"User-Agent": "JadeClient/1.0"})
            with urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError):
            pass
        return None

    def _download_index(self) -> Optional[Dict[str, Any]]:
        """Download the registry index from remote."""
        url = f"{self._registry_url}/index.json"
        try:
            req = Request(url, headers={"User-Agent": "JadeClient/1.0"})
            with urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError):
            pass
        return None

    # ─── Cache Management ───────────────────────────────────────────

    def _load_from_cache(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Load a skill from local cache."""
        cache_file = self._cache_dir / f"{skill_id}.json"
        if cache_file.exists():
            # Check cache freshness (24 hours)
            age = time.time() - cache_file.stat().st_mtime
            if age < 86400:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        return None

    def _save_to_cache(self, skill_id: str, data: Dict[str, Any]) -> None:
        """Save a skill to local cache."""
        cache_file = self._cache_dir / f"{skill_id}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def clear_cache(self) -> int:
        """Clear all cached skills. Returns number of files removed."""
        count = 0
        for f in self._cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        return count

    # ─── Skill Search ───────────────────────────────────────────────

    def search_by_trigger(
        self,
        trigger_type: str,
        conditions: Dict[str, Any],
    ) -> List[JadeSkill]:
        """
        Search loaded skills by trigger conditions.
        This is the core "semantic routing" feature.
        """
        matches: List[JadeSkill] = []
        for skill in self._loaded_skills.values():
            if skill.trigger.type.value == trigger_type:
                if self._match_conditions(skill, conditions):
                    matches.append(skill)
        return matches

    def find_skills_by_trigger(
        self,
        trigger_type: str,
        context: Dict[str, Any],
    ) -> List[JadeSkill]:
        """Alias for search_by_trigger with 'context' parameter name."""
        return self.search_by_trigger(trigger_type, context)

    def _match_conditions(self, skill: JadeSkill, query: Dict[str, Any]) -> bool:
        """Check if a skill's trigger conditions match the query."""
        for cond in skill.trigger.conditions:
            field_val = query.get(cond.field)
            if field_val is None:
                continue

            op = cond.operator.value
            if op == "equals" and field_val == cond.value:
                return True
            elif op == "contains" and isinstance(field_val, str) and cond.value in field_val:
                return True
            elif op == "in" and isinstance(cond.value, list) and field_val in cond.value:
                return True
            elif op == "matches":
                import re
                if re.search(str(cond.value), str(field_val)):
                    return True
        return False

    # ─── Attestation ────────────────────────────────────────────────

    def submit_attestation(
        self,
        skill_id: str,
        success: bool,
        execution_time_ms: int = 0,
        error_message: str = "",
    ) -> bool:
        """
        Submit an execution attestation (success or failure).
        This feeds the Bayesian confidence scoring system.

        In the current implementation, attestations are stored locally.
        In production, they would be submitted as GitHub PRs.
        """
        skill = self._loaded_skills.get(skill_id)
        skill_hash = skill.compute_hash() if skill else ""

        att = Attestation(
            skill_id=skill_id,
            skill_hash=skill_hash,
            success=success,
            execution_time_ms=execution_time_ms,
            attestation_type=AttestationType.SUCCESS if success else AttestationType.FAILURE,
            error_message=error_message,
        )
        try:
            self._registry.submit_attestation(att)
            return True
        except (ValueError, KeyError):
            return False

    # ─── Utility ────────────────────────────────────────────────────

    def get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get summary info about a loaded skill."""
        skill = self._loaded_skills.get(skill_id)
        if not skill:
            return None
        return {
            "skill_id": skill.skill_id,
            "name": skill.metadata.name,
            "version": skill.metadata.version,
            "description": skill.metadata.description,
            "author": skill.metadata.author,
            "tags": skill.metadata.tags,
            "trigger_type": skill.trigger.type.value,
            "node_count": len(skill.execution_dag.nodes),
            "edge_count": len(skill.execution_dag.edges),
            "sandbox_level": skill.security.sandbox_level.value,
            "network_whitelist": skill.security.network_whitelist,
            "hash": skill.compute_hash(),
        }

    def export_skill_list(self) -> List[Dict[str, Any]]:
        """Export a summary list of all loaded skills."""
        results: List[Dict[str, Any]] = []
        for sid in sorted(self._loaded_skills.keys()):
            info = self.get_skill_info(sid)
            if info is not None:
                results.append(info)
        return results
