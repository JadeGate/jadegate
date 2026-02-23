"""
Project JADE - Registry
The "Index" - Global skill registry with confidence scoring and Bayesian updates.

The registry maintains a hash table of verified skills:
    skill_id -> {skill_hash, confidence_score, attestations, ...}

Confidence scores are updated using Bayesian inference:
    P(reliable | evidence) = P(evidence | reliable) * P(reliable) / P(evidence)

In practice, we use a simplified Beta distribution model:
    confidence = (success_count + alpha) / (success_count + failure_count + alpha + beta)

Where alpha=1, beta=1 gives a uniform prior (Laplace smoothing).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    Attestation,
    AttestationType,
    JadeSkill,
    RegistryEntry,
    ValidationIssue,
    ValidationSeverity,
)


# Time decay constants
DECAY_HALF_LIFE_DAYS = 30  # Confidence halves every 30 days without new attestations
DECAY_LAMBDA = math.log(2) / (DECAY_HALF_LIFE_DAYS * 86400)  # Per-second decay rate

# Bayesian prior parameters (Laplace smoothing)
PRIOR_ALPHA = 1.0  # Prior successes
PRIOR_BETA = 1.0   # Prior failures

# Minimum attestations before a skill is considered "verified"
MIN_ATTESTATIONS_FOR_VERIFIED = 3

# Confidence threshold for auto-approval
AUTO_APPROVE_THRESHOLD = 0.8


class JadeRegistry:
    """
    JADE Skill Registry - The "Supreme Court" index.

    Manages:
    1. Skill registration and indexing
    2. Confidence scoring via Bayesian updates
    3. Attestation collection (success/failure reports)
    4. Time-based confidence decay
    5. Skill search and retrieval
    6. Persistence to/from JSON
    """

    def __init__(self, index_path: Optional[str] = None):
        self._entries: Dict[str, RegistryEntry] = {}
        self._attestations: Dict[str, List[Attestation]] = {}
        self._index_path = index_path

        if index_path and os.path.exists(index_path):
            self.load(index_path)

    @property
    def entries(self) -> Dict[str, RegistryEntry]:
        return dict(self._entries)

    @property
    def size(self) -> int:
        return len(self._entries)

    # ─── Registration ───────────────────────────────────────────────

    def register(self, skill: JadeSkill, source_url: str = "") -> RegistryEntry:
        """
        Register a new skill or update an existing one.

        Returns the registry entry.
        """
        skill_hash = skill.compute_hash()
        existing = self._entries.get(skill.skill_id)

        if existing and existing.skill_hash == skill_hash:
            # Same version, no update needed
            return existing

        entry = RegistryEntry(
            skill_id=skill.skill_id,
            skill_hash=skill_hash,
            confidence_score=self._compute_initial_confidence(),
            success_count=0,
            failure_count=0,
            last_verified=time.time(),
            source_url=source_url,
        )

        self._entries[skill.skill_id] = entry
        self._attestations.setdefault(skill.skill_id, [])
        return entry

    def unregister(self, skill_id: str) -> bool:
        """Remove a skill from the registry."""
        if skill_id in self._entries:
            del self._entries[skill_id]
            self._attestations.pop(skill_id, None)
            return True
        return False

    # ─── Attestation & Bayesian Updates ─────────────────────────────

    def submit_attestation(self, attestation: Attestation) -> RegistryEntry:
        """
        Submit a success/failure attestation for a skill.
        Updates the confidence score using Bayesian inference.

        Returns the updated registry entry.
        """
        skill_id = attestation.skill_id
        entry = self._entries.get(skill_id)

        if not entry:
            raise ValueError(f"Skill '{skill_id}' not found in registry")

        # Verify hash matches
        if not attestation.skill_hash:
            return entry  # Reject empty hash attestations
        if attestation.skill_hash != entry.skill_hash:
            raise ValueError(
                f"Attestation hash mismatch for '{skill_id}': "
                f"expected {entry.skill_hash}, got {attestation.skill_hash}"
            )

        # Record attestation
        self._attestations.setdefault(skill_id, []).append(attestation)

        # Update counts
        if attestation.success:
            entry.success_count += 1
        else:
            entry.failure_count += 1

        # Bayesian update
        entry.confidence_score = self._bayesian_confidence(
            entry.success_count, entry.failure_count
        )
        entry.last_verified = time.time()

        return entry

    def batch_submit(self, attestations: List[Attestation]) -> Dict[str, RegistryEntry]:
        """Submit multiple attestations at once."""
        results: Dict[str, RegistryEntry] = {}
        for att in attestations:
            try:
                entry = self.submit_attestation(att)
                results[att.skill_id] = entry
            except ValueError:
                continue
        return results

    def _bayesian_confidence(self, successes: int, failures: int) -> float:
        """
        Compute confidence score using Beta distribution posterior mean.

        P(reliable) = (successes + alpha) / (successes + failures + alpha + beta)

        With Laplace smoothing (alpha=1, beta=1):
        - 0 successes, 0 failures -> 0.5 (maximum uncertainty)
        - 10 successes, 0 failures -> 0.917
        - 100 successes, 1 failure -> 0.990
        - 0 successes, 10 failures -> 0.083
        """
        return (successes + PRIOR_ALPHA) / (successes + failures + PRIOR_ALPHA + PRIOR_BETA)

    def _compute_initial_confidence(self) -> float:
        """Initial confidence for a newly registered skill."""
        return self._bayesian_confidence(0, 0)  # 0.5 with Laplace smoothing

    # ─── Time Decay ─────────────────────────────────────────────────

    def apply_time_decay(self, current_time: Optional[float] = None, days_elapsed: Optional[float] = None) -> int:
        """
        Apply time-based confidence decay to all entries.

        Skills that haven't been attested recently lose confidence.
        Uses exponential decay: C(t) = C(0) * e^(-lambda * dt)

        Args:
            current_time: Absolute timestamp to use as "now"
            days_elapsed: Number of days to simulate decay for (alternative to current_time)

        Returns the number of entries affected.
        """
        if days_elapsed is not None:
            # Simulate decay by shifting last_verified backwards
            now = time.time()
            dt_seconds = days_elapsed * 86400
            affected = 0
            for entry in self._entries.values():
                if dt_seconds > 0:
                    decay_factor = math.exp(-DECAY_LAMBDA * dt_seconds)
                    new_score = entry.confidence_score * decay_factor
                    if abs(new_score - entry.confidence_score) > 0.001:
                        entry.confidence_score = max(0.0, new_score)
                        affected += 1
            return affected

        now = current_time or time.time()
        affected = 0

        for entry in self._entries.values():
            dt = now - entry.last_verified
            if dt > 0:
                decay_factor = math.exp(-DECAY_LAMBDA * dt)
                new_score = entry.confidence_score * decay_factor
                if abs(new_score - entry.confidence_score) > 0.001:
                    entry.confidence_score = max(0.0, new_score)
                    affected += 1

        return affected

    # ─── Pruning ────────────────────────────────────────────────────

    def prune(self, min_confidence: float = 0.1) -> List[str]:
        """
        Remove skills with confidence below threshold.
        Returns list of pruned skill IDs.
        """
        to_prune = [
            sid for sid, entry in self._entries.items()
            if entry.confidence_score < min_confidence
        ]
        for sid in to_prune:
            del self._entries[sid]
            self._attestations.pop(sid, None)
        return to_prune

    # ─── Query ──────────────────────────────────────────────────────

    def get(self, skill_id: str) -> Optional[RegistryEntry]:
        """Get a registry entry by skill ID."""
        return self._entries.get(skill_id)

    def get_entry(self, skill_id: str) -> Optional[RegistryEntry]:
        """Get a registry entry by skill ID (alias for get)."""
        return self._entries.get(skill_id)

    def get_top_skills(self, limit: int = 10) -> List[RegistryEntry]:
        """Get top skills sorted by confidence score descending."""
        return self.search(min_confidence=0.0, max_results=limit, sort_by="confidence_score")

    def search(
        self,
        min_confidence: float = 0.0,
        max_results: int = 50,
        sort_by: str = "confidence_score",
    ) -> List[RegistryEntry]:
        """
        Search the registry with filters.

        Args:
            min_confidence: Minimum confidence score
            max_results: Maximum number of results
            sort_by: Sort field (confidence_score, success_count, last_verified)
        """
        results = [
            e for e in self._entries.values()
            if e.confidence_score >= min_confidence
        ]

        if sort_by == "confidence_score":
            results.sort(key=lambda e: e.confidence_score, reverse=True)
        elif sort_by == "success_count":
            results.sort(key=lambda e: e.success_count, reverse=True)
        elif sort_by == "last_verified":
            results.sort(key=lambda e: e.last_verified, reverse=True)

        return results[:max_results]

    def get_verified_skills(self) -> List[RegistryEntry]:
        """Get all skills that meet the minimum attestation threshold."""
        return [
            e for e in self._entries.values()
            if (e.success_count + e.failure_count) >= MIN_ATTESTATIONS_FOR_VERIFIED
            and e.confidence_score >= AUTO_APPROVE_THRESHOLD
        ]

    def get_attestations(self, skill_id: str) -> List[Attestation]:
        """Get all attestations for a skill."""
        return list(self._attestations.get(skill_id, []))

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total = len(self._entries)
        if total == 0:
            return {
                "total_skills": 0,
                "verified_skills": 0,
                "avg_confidence": 0.0,
                "total_attestations": 0,
            }

        verified = len(self.get_verified_skills())
        avg_conf = sum(e.confidence_score for e in self._entries.values()) / total
        total_att = sum(len(atts) for atts in self._attestations.values())

        return {
            "total_skills": total,
            "verified_skills": verified,
            "avg_confidence": round(avg_conf, 4),
            "total_attestations": total_att,
        }

    # ─── Persistence ────────────────────────────────────────────────

    def save(self, path: Optional[str] = None) -> str:
        """Save registry to JSON file."""
        save_path = path or self._index_path
        if not save_path:
            raise ValueError("No save path specified")

        data = {
            "jade_registry_version": "1.0.0",
            "generated_at": time.time(),
            "stats": self.get_stats(),
            "entries": {
                sid: entry.to_dict()
                for sid, entry in self._entries.items()
            },
        }

        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return save_path

    def load(self, path: Optional[str] = None) -> int:
        """
        Load registry from JSON file.
        Returns number of entries loaded.
        """
        load_path = path or self._index_path
        if not load_path or not os.path.exists(load_path):
            return 0

        with open(load_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("entries", {})
        for sid, entry_data in entries.items():
            self._entries[sid] = RegistryEntry.from_dict(entry_data)
            self._attestations.setdefault(sid, [])

        return len(entries)

    def export_index(self) -> Dict[str, Any]:
        """Export the registry as a minimal index (for GitHub publishing)."""
        index: Dict[str, Any] = {}
        for sid, entry in self._entries.items():
            index[sid] = {
                "skill_hash": entry.skill_hash,
                "confidence_score": round(entry.confidence_score, 4),
                "success_count": entry.success_count,
                "failure_count": entry.failure_count,
                "verified": (
                    (entry.success_count + entry.failure_count) >= MIN_ATTESTATIONS_FOR_VERIFIED
                    and entry.confidence_score >= AUTO_APPROVE_THRESHOLD
                ),
            }
        return {
            "jade_index_version": "1.0.0",
            "generated_at": time.time(),
            "total_skills": len(index),
            "skills": index,
        }
