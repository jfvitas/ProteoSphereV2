from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from core.release.cohort_registry import ReleaseCohortEntry, ReleaseCohortRegistry

ReleaseCompletenessGrade = Literal[
    "release_ready",
    "nearly_ready",
    "partial",
    "blocked",
    "excluded",
]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


@dataclass(frozen=True, slots=True)
class ReleaseCompletenessScore:
    canonical_id: str
    grade: ReleaseCompletenessGrade
    score: int
    release_ready: bool
    blocker_count: int
    evidence_lane_count: int
    source_manifest_count: int
    packet_ready: bool | None
    rationale: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_id": self.canonical_id,
            "grade": self.grade,
            "score": self.score,
            "release_ready": self.release_ready,
            "blocker_count": self.blocker_count,
            "evidence_lane_count": self.evidence_lane_count,
            "source_manifest_count": self.source_manifest_count,
            "packet_ready": self.packet_ready,
            "rationale": list(self.rationale),
        }


@dataclass(frozen=True, slots=True)
class ReleaseCompletenessReport:
    registry_id: str
    release_version: str
    grade_counts: Mapping[str, int]
    release_ready_count: int
    blocked_count: int
    scores: tuple[ReleaseCompletenessScore, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "registry_id": self.registry_id,
            "release_version": self.release_version,
            "grade_counts": dict(self.grade_counts),
            "release_ready_count": self.release_ready_count,
            "blocked_count": self.blocked_count,
            "scores": [score.to_dict() for score in self.scores],
        }


def score_release_cohort_entry(entry: ReleaseCohortEntry) -> ReleaseCompletenessScore:
    if not isinstance(entry, ReleaseCohortEntry):
        raise TypeError("entry must be a ReleaseCohortEntry")

    evidence_lane_count = len(entry.evidence_lanes)
    source_manifest_count = len(entry.source_manifest_ids)
    blocker_count = len(entry.blocker_ids)
    rationale: list[str] = [
        f"inclusion_status={entry.inclusion_status}",
        f"freeze_state={entry.freeze_state}",
        f"evidence_lanes={evidence_lane_count}",
        f"source_manifests={source_manifest_count}",
        f"blockers={blocker_count}",
        f"packet_ready={entry.packet_ready}",
    ]

    if entry.inclusion_status == "excluded":
        return ReleaseCompletenessScore(
            canonical_id=entry.canonical_id,
            grade="excluded",
            score=0,
            release_ready=False,
            blocker_count=blocker_count,
            evidence_lane_count=evidence_lane_count,
            source_manifest_count=source_manifest_count,
            packet_ready=entry.packet_ready,
            rationale=tuple(
                [
                    *rationale,
                    f"excluded_reason={entry.exclusion_reason or 'not_provided'}",
                ]
            ),
        )

    score = 0
    if entry.inclusion_status == "included":
        score += 40
    elif entry.inclusion_status == "candidate":
        score += 20
    else:
        score += 10

    if entry.freeze_state == "frozen":
        score += 20
    elif entry.freeze_state == "draft":
        score += 5

    score += min(20, evidence_lane_count * 5)
    score += min(10, source_manifest_count * 3)

    if entry.packet_ready is True:
        score += 10
    elif entry.packet_ready is None:
        score += 3

    if entry.benchmark_priority is not None:
        score += max(0, 10 - entry.benchmark_priority)
        rationale.append(f"benchmark_priority={entry.benchmark_priority}")

    if blocker_count:
        score -= min(45, blocker_count * 15)
        rationale.extend(f"blocker={blocker}" for blocker in entry.blocker_ids)

    score = _clamp_score(score)

    if entry.release_ready and score >= 85:
        grade: ReleaseCompletenessGrade = "release_ready"
    elif entry.inclusion_status == "included" and not entry.blocker_ids and score >= 65:
        grade = "nearly_ready"
    elif blocker_count:
        grade = "blocked"
    else:
        grade = "partial"

    return ReleaseCompletenessScore(
        canonical_id=entry.canonical_id,
        grade=grade,
        score=score,
        release_ready=entry.release_ready,
        blocker_count=blocker_count,
        evidence_lane_count=evidence_lane_count,
        source_manifest_count=source_manifest_count,
        packet_ready=entry.packet_ready,
        rationale=tuple(rationale),
    )


def score_release_cohort_registry(
    registry: ReleaseCohortRegistry | Mapping[str, Any],
) -> ReleaseCompletenessReport:
    normalized_registry = (
        registry
        if isinstance(registry, ReleaseCohortRegistry)
        else ReleaseCohortRegistry.from_dict(dict(registry))
    )
    scores = tuple(score_release_cohort_entry(entry) for entry in normalized_registry.entries)
    grade_counts = Counter(score.grade for score in scores)
    return ReleaseCompletenessReport(
        registry_id=normalized_registry.registry_id,
        release_version=normalized_registry.release_version,
        grade_counts=dict(grade_counts),
        release_ready_count=sum(1 for score in scores if score.release_ready),
        blocked_count=sum(1 for score in scores if score.grade == "blocked"),
        scores=scores,
    )


__all__ = [
    "ReleaseCompletenessGrade",
    "ReleaseCompletenessReport",
    "ReleaseCompletenessScore",
    "score_release_cohort_entry",
    "score_release_cohort_registry",
]
