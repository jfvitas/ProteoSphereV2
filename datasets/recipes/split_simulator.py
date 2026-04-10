from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from datasets.recipes.schema import RecipeEvaluationContext, TrainingRecipeSchema

DEFAULT_SIMULATION_SPLITS: tuple[str, ...] = ("train", "val", "test")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        iterable = (values,)
    else:
        iterable = tuple(values)
    ordered: dict[str, str] = {}
    for value in iterable:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise TypeError("value must be an integer or None")
    return int(value)


@dataclass(frozen=True, slots=True)
class SplitSimulationCandidate:
    canonical_id: str
    leakage_key: str
    preferred_split: str | None = None
    linked_group_id: str | None = None
    lane_depth: int = 0
    bucket: str | None = None
    validation_class: str | None = None
    evidence_lanes: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_id", _clean_text(self.canonical_id))
        object.__setattr__(self, "leakage_key", _clean_text(self.leakage_key))
        object.__setattr__(self, "preferred_split", _optional_text(self.preferred_split))
        object.__setattr__(self, "linked_group_id", _optional_text(self.linked_group_id))
        object.__setattr__(self, "lane_depth", _normalize_int_or_none(self.lane_depth) or 0)
        object.__setattr__(self, "bucket", _optional_text(self.bucket))
        object.__setattr__(self, "validation_class", _optional_text(self.validation_class))
        object.__setattr__(self, "evidence_lanes", _clean_text_tuple(self.evidence_lanes))
        object.__setattr__(self, "blocker_ids", _clean_text_tuple(self.blocker_ids))
        object.__setattr__(self, "payload", dict(self.payload))
        if not self.canonical_id:
            raise ValueError("canonical_id must not be empty")
        if not self.leakage_key:
            raise ValueError("leakage_key must not be empty")

    @property
    def group_key(self) -> str:
        return self.linked_group_id or self.leakage_key or self.canonical_id

    def evaluation_payload(self) -> dict[str, Any]:
        payload = dict(self.payload)
        payload.setdefault("canonical_id", self.canonical_id)
        payload.setdefault("leakage_key", self.leakage_key)
        payload.setdefault("split", self.preferred_split)
        payload.setdefault("linked_group_id", self.linked_group_id)
        payload.setdefault("lane_depth", self.lane_depth)
        payload.setdefault("bucket", self.bucket)
        payload.setdefault("validation_class", self.validation_class)
        payload.setdefault("evidence_lanes", self.evidence_lanes)
        payload.setdefault("blocker_ids", self.blocker_ids)
        metadata = payload.get("metadata")
        if isinstance(metadata, Mapping):
            payload.setdefault("lane_depth", metadata.get("lane_depth", self.lane_depth))
            payload.setdefault("bucket", metadata.get("bucket", self.bucket))
            payload.setdefault(
                "validation_class",
                metadata.get("validation_class", self.validation_class),
            )
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SplitSimulationCandidate:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        metadata = payload.get("metadata") or {}
        return cls(
            canonical_id=payload.get("canonical_id") or "",
            leakage_key=payload.get("leakage_key") or "",
            preferred_split=payload.get("split") or payload.get("preferred_split"),
            linked_group_id=payload.get("linked_group_id") or metadata.get("linked_group_id"),
            lane_depth=metadata.get("lane_depth") or payload.get("lane_depth") or 0,
            bucket=metadata.get("bucket") or payload.get("bucket"),
            validation_class=metadata.get("validation_class") or payload.get("validation_class"),
            evidence_lanes=payload.get("evidence_lanes") or (),
            blocker_ids=payload.get("blocker_ids") or (),
            payload=dict(payload),
        )


@dataclass(frozen=True, slots=True)
class SplitSimulationAssignment:
    canonical_id: str
    split_name: str
    leakage_key: str
    linked_group_id: str
    lane_depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "split_name": self.split_name,
            "leakage_key": self.leakage_key,
            "linked_group_id": self.linked_group_id,
            "lane_depth": self.lane_depth,
        }


@dataclass(frozen=True, slots=True)
class SplitSimulationRejected:
    canonical_id: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"canonical_id": self.canonical_id, "reasons": list(self.reasons)}


@dataclass(frozen=True, slots=True)
class SplitSimulationResult:
    recipe_id: str
    assignments: tuple[SplitSimulationAssignment, ...]
    rejected: tuple[SplitSimulationRejected, ...]
    split_counts: Mapping[str, int]
    target_counts: Mapping[str, int]
    linked_group_count: int
    leakage_collisions: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    lane_depth_by_split: Mapping[str, Mapping[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "assignments": [assignment.to_dict() for assignment in self.assignments],
            "rejected": [item.to_dict() for item in self.rejected],
            "split_counts": dict(self.split_counts),
            "target_counts": dict(self.target_counts),
            "linked_group_count": self.linked_group_count,
            "leakage_collisions": list(self.leakage_collisions),
            "notes": list(self.notes),
            "lane_depth_by_split": {
                split: dict(values) for split, values in self.lane_depth_by_split.items()
            },
        }


def _default_target_counts(candidates: Iterable[SplitSimulationCandidate]) -> dict[str, int]:
    candidates_tuple = tuple(candidates)
    total = len(candidates_tuple)
    if total == 0:
        return {split: 0 for split in DEFAULT_SIMULATION_SPLITS}
    raw = {"train": total * 0.7, "val": total * 0.15, "test": total * 0.15}
    targets = {split: int(value) for split, value in raw.items()}
    remainder = total - sum(targets.values())
    for split in DEFAULT_SIMULATION_SPLITS[:remainder]:
        targets[split] += 1
    return targets


def _choose_split(
    *,
    group_size: int,
    preferred_split: str | None,
    split_counts: Mapping[str, int],
    target_counts: Mapping[str, int],
) -> str:
    available_splits = tuple(target_counts) or DEFAULT_SIMULATION_SPLITS
    if preferred_split in available_splits:
        return preferred_split
    best_split = available_splits[0]
    best_score: tuple[int, int] | None = None
    for index, split_name in enumerate(available_splits):
        projected = split_counts.get(split_name, 0) + group_size
        overflow = max(0, projected - target_counts.get(split_name, 0))
        score = (overflow, split_counts.get(split_name, 0), index)
        if best_score is None or score < best_score:
            best_score = score
            best_split = split_name
    return best_split


def _lane_depth_summary(
    assignments: Iterable[SplitSimulationAssignment],
) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for assignment in assignments:
        grouped[assignment.split_name].append(assignment.lane_depth)
    summary: dict[str, dict[str, float]] = {}
    for split_name, values in grouped.items():
        summary[split_name] = {
            "count": float(len(values)),
            "avg_lane_depth": float(sum(values) / len(values)),
            "min_lane_depth": float(min(values)),
            "max_lane_depth": float(max(values)),
        }
    return summary


def simulate_recipe_splits(
    recipe: TrainingRecipeSchema,
    candidates: Iterable[SplitSimulationCandidate | Mapping[str, Any]],
) -> SplitSimulationResult:
    if not isinstance(recipe, TrainingRecipeSchema):
        raise TypeError("recipe must be a TrainingRecipeSchema")

    normalized_candidates = tuple(
        candidate
        if isinstance(candidate, SplitSimulationCandidate)
        else SplitSimulationCandidate.from_dict(candidate)
        for candidate in candidates
    )
    target_counts = dict(recipe.target_splits) or _default_target_counts(normalized_candidates)
    split_counts = {split_name: 0 for split_name in target_counts}

    accepted: list[SplitSimulationCandidate] = []
    rejected: list[SplitSimulationRejected] = []
    occupied_keys: set[str] = set()
    leakage_collisions: set[str] = set()

    for candidate in normalized_candidates:
        candidate_payload = candidate.evaluation_payload()
        evaluation = recipe.evaluate_candidate(
            candidate_payload,
            context=RecipeEvaluationContext(occupied_leakage_keys=tuple(occupied_keys)),
        )
        if evaluation.accepted:
            accepted.append(candidate)
            if candidate.leakage_key in occupied_keys:
                leakage_collisions.add(candidate.leakage_key)
            occupied_keys.add(candidate.leakage_key)
        else:
            rejected.append(
                SplitSimulationRejected(
                    canonical_id=candidate.canonical_id,
                    reasons=evaluation.reasons,
                )
            )

    groups: dict[str, list[SplitSimulationCandidate]] = defaultdict(list)
    for candidate in accepted:
        groups[candidate.group_key].append(candidate)

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: (
            -len(item[1]),
            -max(candidate.lane_depth for candidate in item[1]),
            item[0],
        ),
    )
    assignments: list[SplitSimulationAssignment] = []
    for group_key, group_candidates in ordered_groups:
        preferred_split = group_candidates[0].preferred_split
        split_name = _choose_split(
            group_size=len(group_candidates),
            preferred_split=preferred_split,
            split_counts=split_counts,
            target_counts=target_counts,
        )
        split_counts[split_name] = split_counts.get(split_name, 0) + len(group_candidates)
        for candidate in group_candidates:
            assignments.append(
                SplitSimulationAssignment(
                    canonical_id=candidate.canonical_id,
                    split_name=split_name,
                    leakage_key=candidate.leakage_key,
                    linked_group_id=group_key,
                    lane_depth=candidate.lane_depth,
                )
            )

    notes = []
    if leakage_collisions:
        notes.append("leakage collisions remained after acceptance filtering")
    if any(
        split_counts.get(split_name, 0) != target_counts.get(split_name, 0)
        for split_name in target_counts
    ):
        notes.append("simulated split counts do not exactly match requested targets")

    assignments = sorted(assignments, key=lambda item: (item.split_name, item.canonical_id))
    rejected = sorted(rejected, key=lambda item: item.canonical_id)
    return SplitSimulationResult(
        recipe_id=recipe.recipe_id,
        assignments=tuple(assignments),
        rejected=tuple(rejected),
        split_counts=split_counts,
        target_counts=target_counts,
        linked_group_count=len(groups),
        leakage_collisions=tuple(sorted(leakage_collisions)),
        notes=tuple(notes),
        lane_depth_by_split=_lane_depth_summary(assignments),
    )


__all__ = [
    "DEFAULT_SIMULATION_SPLITS",
    "SplitSimulationAssignment",
    "SplitSimulationCandidate",
    "SplitSimulationRejected",
    "SplitSimulationResult",
    "simulate_recipe_splits",
]
