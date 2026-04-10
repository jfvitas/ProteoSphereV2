from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

_EVIDENCE_WEIGHTS = {
    "direct_live_smoke": 1.0,
    "live_summary_library_probe": 0.7,
    "in_tree_live_snapshot": 0.55,
    "live_verified_accession": 0.45,
    "bridge_upgrade": 0.6,
    "probe_backed": 0.35,
}
_BUCKET_WEIGHTS = {
    "rich_coverage": 0.25,
    "moderate_coverage": 0.15,
    "thin_coverage": -0.1,
    "unknown": 0.0,
}


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


def _as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise TypeError("value must be an integer")
    return int(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise TypeError("value must be a bool")


@dataclass(frozen=True, slots=True)
class BalancedCohortCandidate:
    canonical_id: str
    leakage_key: str
    requested_modalities: tuple[str, ...] = ()
    present_modalities: tuple[str, ...] = ()
    missing_modalities: tuple[str, ...] = ()
    source_lanes: tuple[str, ...] = ()
    lane_depth: int = 0
    evidence_mode: str | None = None
    validation_class: str | None = None
    bucket: str | None = None
    linked_group_id: str | None = None
    record_type: str | None = None
    packet_ready: bool = False
    thin_coverage: bool = False
    mixed_evidence: bool = False
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_id", _clean_text(self.canonical_id))
        object.__setattr__(self, "leakage_key", _clean_text(self.leakage_key))
        object.__setattr__(
            self,
            "requested_modalities",
            _clean_text_tuple(self.requested_modalities),
        )
        object.__setattr__(self, "present_modalities", _clean_text_tuple(self.present_modalities))
        object.__setattr__(self, "missing_modalities", _clean_text_tuple(self.missing_modalities))
        object.__setattr__(self, "source_lanes", _clean_text_tuple(self.source_lanes))
        object.__setattr__(self, "lane_depth", _as_int(self.lane_depth, 0))
        object.__setattr__(self, "evidence_mode", _optional_text(self.evidence_mode))
        object.__setattr__(self, "validation_class", _optional_text(self.validation_class))
        object.__setattr__(self, "bucket", _optional_text(self.bucket) or "unknown")
        object.__setattr__(self, "linked_group_id", _optional_text(self.linked_group_id))
        object.__setattr__(self, "record_type", _optional_text(self.record_type))
        object.__setattr__(self, "packet_ready", _as_bool(self.packet_ready))
        object.__setattr__(self, "thin_coverage", _as_bool(self.thin_coverage))
        object.__setattr__(self, "mixed_evidence", _as_bool(self.mixed_evidence))
        object.__setattr__(self, "payload", dict(self.payload))
        if not self.canonical_id:
            raise ValueError("canonical_id must not be empty")
        if not self.leakage_key:
            raise ValueError("leakage_key must not be empty")

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        requested_modalities: Iterable[str] = (),
    ) -> BalancedCohortCandidate:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            canonical_id=payload.get("canonical_id") or "",
            leakage_key=payload.get("leakage_key") or "",
            requested_modalities=tuple(requested_modalities),
            present_modalities=payload.get("present_modalities") or (),
            missing_modalities=payload.get("missing_modalities") or (),
            source_lanes=payload.get("source_lanes") or payload.get("evidence_lanes") or (),
            lane_depth=payload.get("lane_depth") or 0,
            evidence_mode=payload.get("evidence_mode"),
            validation_class=payload.get("validation_class"),
            bucket=payload.get("bucket") or payload.get("grade") or "unknown",
            linked_group_id=payload.get("linked_group_id"),
            record_type=payload.get("record_type"),
            packet_ready=payload.get("packet_ready", False),
            thin_coverage=payload.get("thin_coverage", False),
            mixed_evidence=payload.get("mixed_evidence", False),
            payload=dict(payload),
        )


@dataclass(frozen=True, slots=True)
class BalancedCohortScore:
    canonical_id: str
    leakage_key: str
    accepted: bool
    total_score: float
    component_scores: Mapping[str, float]
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "leakage_key": self.leakage_key,
            "accepted": self.accepted,
            "total_score": self.total_score,
            "component_scores": dict(self.component_scores),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class BalancedCohortRanking:
    accepted: tuple[BalancedCohortScore, ...]
    rejected: tuple[BalancedCohortScore, ...]
    requested_modalities: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": [item.to_dict() for item in self.accepted],
            "rejected": [item.to_dict() for item in self.rejected],
            "requested_modalities": list(self.requested_modalities),
        }


def _completeness_score(candidate: BalancedCohortCandidate) -> float:
    requested = candidate.requested_modalities
    if not requested:
        present = len(candidate.present_modalities)
        missing = len(candidate.missing_modalities)
        total = present + missing
        return 0.0 if total <= 0 else present / total

    missing = {item.casefold() for item in candidate.missing_modalities}
    satisfied = sum(1 for item in requested if item.casefold() not in missing)
    return satisfied / len(requested)


def _depth_score(candidate: BalancedCohortCandidate) -> float:
    return min(candidate.lane_depth, 6) / 6.0


def _evidence_score(candidate: BalancedCohortCandidate) -> float:
    evidence_mode = (candidate.evidence_mode or "").casefold()
    return _EVIDENCE_WEIGHTS.get(evidence_mode, 0.25)


def _diversity_score(
    candidate: BalancedCohortCandidate,
    selected_candidates: tuple[BalancedCohortCandidate, ...],
) -> float:
    if not selected_candidates:
        return 0.15

    selected_buckets = {item.bucket.casefold() for item in selected_candidates if item.bucket}
    selected_validation = {
        item.validation_class.casefold()
        for item in selected_candidates
        if item.validation_class
    }
    selected_evidence = {
        item.evidence_mode.casefold() for item in selected_candidates if item.evidence_mode
    }
    selected_lanes = {
        lane.casefold()
        for item in selected_candidates
        for lane in item.source_lanes
    }

    score = 0.0
    if candidate.bucket and candidate.bucket.casefold() not in selected_buckets:
        score += 0.08
    if (
        candidate.validation_class
        and candidate.validation_class.casefold() not in selected_validation
    ):
        score += 0.08
    if candidate.evidence_mode and candidate.evidence_mode.casefold() not in selected_evidence:
        score += 0.06

    new_lanes = sum(
        1 for lane in candidate.source_lanes if lane.casefold() not in selected_lanes
    )
    score += min(new_lanes * 0.03, 0.12)

    if (
        candidate.linked_group_id
        and any(item.linked_group_id == candidate.linked_group_id for item in selected_candidates)
    ):
        score -= 0.05
    return score


def score_candidate(
    candidate: BalancedCohortCandidate | Mapping[str, Any],
    *,
    requested_modalities: Iterable[str] = (),
    selected_candidates: Iterable[BalancedCohortCandidate | Mapping[str, Any]] = (),
) -> BalancedCohortScore:
    normalized = (
        candidate
        if isinstance(candidate, BalancedCohortCandidate)
        else BalancedCohortCandidate.from_dict(
            candidate,
            requested_modalities=requested_modalities,
        )
    )
    selected = tuple(
        item
        if isinstance(item, BalancedCohortCandidate)
        else BalancedCohortCandidate.from_dict(
            item,
            requested_modalities=requested_modalities,
        )
        for item in selected_candidates
    )

    reasons: list[str] = []
    if normalized.leakage_key in {item.leakage_key for item in selected}:
        reasons.append(f"leakage_key={normalized.leakage_key} already selected")

    completeness = _completeness_score(normalized)
    depth = _depth_score(normalized)
    evidence = _evidence_score(normalized)
    diversity = _diversity_score(normalized, selected)

    packet_bonus = 0.1 if normalized.packet_ready else 0.0
    bucket_weight = _BUCKET_WEIGHTS.get(normalized.bucket.casefold(), 0.0)
    penalties = 0.0
    if normalized.thin_coverage:
        penalties += 0.15
        reasons.append("thin_coverage penalty")
    if normalized.mixed_evidence:
        penalties += 0.1
        reasons.append("mixed_evidence penalty")

    total = (
        completeness * 0.4
        + depth * 0.2
        + evidence * 0.2
        + diversity
        + packet_bonus
        + bucket_weight
        - penalties
    )
    components = {
        "completeness": round(completeness, 4),
        "depth": round(depth, 4),
        "evidence": round(evidence, 4),
        "diversity": round(diversity, 4),
        "packet_bonus": round(packet_bonus, 4),
        "bucket_weight": round(bucket_weight, 4),
        "penalties": round(penalties, 4),
    }
    return BalancedCohortScore(
        canonical_id=normalized.canonical_id,
        leakage_key=normalized.leakage_key,
        accepted=not reasons or all("penalty" in reason for reason in reasons),
        total_score=round(total, 4),
        component_scores=components,
        reasons=tuple(reasons),
    )


def rank_candidates(
    candidates: Iterable[BalancedCohortCandidate | Mapping[str, Any]],
    *,
    requested_modalities: Iterable[str] = (),
    limit: int | None = None,
) -> BalancedCohortRanking:
    normalized_candidates = [
        item
        if isinstance(item, BalancedCohortCandidate)
        else BalancedCohortCandidate.from_dict(item, requested_modalities=requested_modalities)
        for item in candidates
    ]
    selected_candidates: list[BalancedCohortCandidate] = []
    accepted_scores: list[BalancedCohortScore] = []
    remaining = list(normalized_candidates)

    while remaining and (limit is None or len(selected_candidates) < limit):
        scored_candidates = [
            (
                score_candidate(
                    item,
                    requested_modalities=requested_modalities,
                    selected_candidates=selected_candidates,
                ),
                item,
            )
            for item in remaining
        ]
        selectable = [item for item in scored_candidates if item[0].accepted]
        if not selectable:
            break
        selectable.sort(
            key=lambda item: (
                -item[0].total_score,
                -item[1].lane_depth,
                item[1].canonical_id,
            )
        )
        chosen_score, chosen_candidate = selectable[0]
        accepted_scores.append(chosen_score)
        selected_candidates.append(chosen_candidate)
        remaining = [
            item
            for item in remaining
            if item.canonical_id != chosen_candidate.canonical_id
        ]

    rejected_scores: list[BalancedCohortScore] = []
    for item in remaining:
        score = score_candidate(
            item,
            requested_modalities=requested_modalities,
            selected_candidates=selected_candidates,
        )
        reasons = list(score.reasons)
        if not reasons and limit is not None and len(selected_candidates) >= limit:
            reasons.append("selection_limit_reached")
        rejected_scores.append(
            BalancedCohortScore(
                canonical_id=score.canonical_id,
                leakage_key=score.leakage_key,
                accepted=False,
                total_score=score.total_score,
                component_scores=score.component_scores,
                reasons=tuple(reasons),
            )
        )

    return BalancedCohortRanking(
        accepted=tuple(accepted_scores),
        rejected=tuple(rejected_scores),
        requested_modalities=_clean_text_tuple(requested_modalities),
    )
