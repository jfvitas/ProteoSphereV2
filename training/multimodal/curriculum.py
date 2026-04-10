from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

CurriculumExampleState = Literal["anchor", "progressive", "thin", "mixed", "blocked"]
HardNegativeDecisionState = Literal["selected", "blocked"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _value_get(value: Any, *keys: str) -> Any:
    if isinstance(value, Mapping):
        for key in keys:
            if key in value and value[key] is not None:
                return value[key]
        return None
    for key in keys:
        if hasattr(value, key):
            result = getattr(value, key)
            if result is not None:
                return result
    return None


def _normalize_status(value: Any) -> str:
    status = _clean_text(value).casefold()
    return status or "ready"


def _stage_rank(state: CurriculumExampleState) -> int:
    return {
        "anchor": 0,
        "progressive": 1,
        "thin": 2,
        "mixed": 3,
        "blocked": 4,
    }[state]


@dataclass(frozen=True, slots=True)
class CurriculumExample:
    example_id: str
    evidence_depth: int
    thin_coverage: bool = False
    mixed_evidence: bool = False
    status: str = "ready"
    present_modalities: tuple[str, ...] = ()
    missing_modalities: tuple[str, ...] = ()
    source_lanes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "example_id", _required_text(self.example_id, "example_id"))
        object.__setattr__(self, "evidence_depth", int(self.evidence_depth))
        object.__setattr__(self, "thin_coverage", bool(self.thin_coverage))
        object.__setattr__(self, "mixed_evidence", bool(self.mixed_evidence))
        object.__setattr__(self, "status", _normalize_status(self.status))
        object.__setattr__(self, "present_modalities", _dedupe_text(self.present_modalities))
        object.__setattr__(self, "missing_modalities", _dedupe_text(self.missing_modalities))
        object.__setattr__(self, "source_lanes", _dedupe_text(self.source_lanes))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if self.evidence_depth < 0:
            raise ValueError("evidence_depth must be non-negative")
        if self.status not in {"ready", "partial", "blocked", "unresolved"}:
            raise ValueError("status must be ready, partial, blocked, or unresolved")

    @property
    def curriculum_state(self) -> CurriculumExampleState:
        if self.status in {"blocked", "unresolved"}:
            return "blocked"
        if self.mixed_evidence:
            return "mixed"
        if self.thin_coverage or self.evidence_depth <= 1:
            return "thin"
        if self.evidence_depth >= 4:
            return "anchor"
        return "progressive"

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "evidence_depth": self.evidence_depth,
            "thin_coverage": self.thin_coverage,
            "mixed_evidence": self.mixed_evidence,
            "status": self.status,
            "present_modalities": list(self.present_modalities),
            "missing_modalities": list(self.missing_modalities),
            "source_lanes": list(self.source_lanes),
            "notes": list(self.notes),
            "curriculum_state": self.curriculum_state,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CurriculumExample:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            example_id=payload.get("example_id") or payload.get("id") or "",
            evidence_depth=int(payload.get("evidence_depth") or 0),
            thin_coverage=bool(payload.get("thin_coverage")),
            mixed_evidence=bool(payload.get("mixed_evidence")),
            status=payload.get("status") or "ready",
            present_modalities=payload.get("present_modalities") or (),
            missing_modalities=payload.get("missing_modalities") or (),
            source_lanes=payload.get("source_lanes") or (),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class HardNegativeCandidate:
    candidate_id: str
    evidence_depth: int | None = None
    thin_coverage: bool = False
    mixed_evidence: bool = False
    status: str = "ready"
    source_lanes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    unresolved_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _required_text(self.candidate_id, "candidate_id"))
        object.__setattr__(self, "thin_coverage", bool(self.thin_coverage))
        object.__setattr__(self, "mixed_evidence", bool(self.mixed_evidence))
        object.__setattr__(self, "status", _normalize_status(self.status))
        object.__setattr__(self, "source_lanes", _dedupe_text(self.source_lanes))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        object.__setattr__(self, "unresolved_reason", _optional_text(self.unresolved_reason))
        if self.status not in {"ready", "partial", "blocked", "unresolved"}:
            raise ValueError("status must be ready, partial, blocked, or unresolved")
        if self.evidence_depth is not None and self.evidence_depth < 0:
            raise ValueError("evidence_depth must be non-negative")

    @property
    def eligible(self) -> bool:
        return (
            self.status == "ready"
            and self.evidence_depth is not None
            and not self.unresolved_reason
        )

    def score(self) -> int:
        if not self.eligible:
            raise ValueError("ineligible hard-negative candidates do not have a score")
        assert self.evidence_depth is not None
        score = self.evidence_depth * 10
        if self.mixed_evidence:
            score += 15
        if self.thin_coverage:
            score -= 5
        score += len(self.source_lanes)
        return score

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "evidence_depth": self.evidence_depth,
            "thin_coverage": self.thin_coverage,
            "mixed_evidence": self.mixed_evidence,
            "status": self.status,
            "source_lanes": list(self.source_lanes),
            "notes": list(self.notes),
            "unresolved_reason": self.unresolved_reason,
            "eligible": self.eligible,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HardNegativeCandidate:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        evidence_depth = payload.get("evidence_depth")
        return cls(
            candidate_id=payload.get("candidate_id") or payload.get("example_id") or "",
            evidence_depth=None if evidence_depth in (None, "") else int(evidence_depth),
            thin_coverage=bool(payload.get("thin_coverage")),
            mixed_evidence=bool(payload.get("mixed_evidence")),
            status=payload.get("status") or "ready",
            source_lanes=payload.get("source_lanes") or (),
            notes=payload.get("notes") or payload.get("note") or (),
            unresolved_reason=payload.get("unresolved_reason") or payload.get("reason"),
        )


@dataclass(frozen=True, slots=True)
class HardNegativeDecision:
    candidate_id: str
    decision: HardNegativeDecisionState
    score: int | None
    reason: str
    candidate: HardNegativeCandidate | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _required_text(self.candidate_id, "candidate_id"))
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        if self.decision not in {"selected", "blocked"}:
            raise ValueError("decision must be selected or blocked")
        if self.score is not None and self.score < 0:
            raise ValueError("score must be non-negative when provided")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "decision": self.decision,
            "score": self.score,
            "reason": self.reason,
            "candidate": None if self.candidate is None else self.candidate.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class HardNegativeSelection:
    decisions: tuple[HardNegativeDecision, ...]
    limit: int

    def __post_init__(self) -> None:
        if self.limit < 0:
            raise ValueError("limit must be non-negative")
        object.__setattr__(self, "decisions", tuple(self.decisions))

    @property
    def selected_candidate_ids(self) -> tuple[str, ...]:
        return tuple(
            decision.candidate_id for decision in self.decisions if decision.decision == "selected"
        )

    @property
    def blocked_candidate_ids(self) -> tuple[str, ...]:
        return tuple(
            decision.candidate_id for decision in self.decisions if decision.decision == "blocked"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "limit": self.limit,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "blocked_candidate_ids": list(self.blocked_candidate_ids),
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


@dataclass(frozen=True, slots=True)
class CurriculumSchedule:
    examples: tuple[CurriculumExample, ...]
    hard_negatives: HardNegativeSelection
    stage: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "examples", tuple(self.examples))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    @property
    def ordered_example_ids(self) -> tuple[str, ...]:
        return tuple(example.example_id for example in self.examples)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "ordered_example_ids": list(self.ordered_example_ids),
            "examples": [example.to_dict() for example in self.examples],
            "hard_negatives": self.hard_negatives.to_dict(),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class CurriculumScheduler:
    hard_negative_limit: int = 1
    min_anchor_depth: int = 4
    min_progressive_depth: int = 2

    def __post_init__(self) -> None:
        if self.hard_negative_limit < 0:
            raise ValueError("hard_negative_limit must be non-negative")
        if self.min_anchor_depth < 1:
            raise ValueError("min_anchor_depth must be >= 1")
        if self.min_progressive_depth < 1:
            raise ValueError("min_progressive_depth must be >= 1")
        if self.min_progressive_depth > self.min_anchor_depth:
            raise ValueError("min_progressive_depth must be <= min_anchor_depth")

    def stage_for_example(
        self,
        example: CurriculumExample | Mapping[str, Any],
    ) -> CurriculumExampleState:
        item = (
            example
            if isinstance(example, CurriculumExample)
            else CurriculumExample.from_dict(example)
        )
        if item.status in {"blocked", "unresolved"}:
            return "blocked"
        if item.mixed_evidence:
            return "mixed"
        if item.thin_coverage or item.evidence_depth <= 1:
            return "thin"
        if item.evidence_depth >= self.min_anchor_depth:
            return "anchor"
        return "progressive"

    def rank_examples(
        self,
        examples: Iterable[CurriculumExample | Mapping[str, Any]],
    ) -> tuple[CurriculumExample, ...]:
        normalized = tuple(
            item if isinstance(item, CurriculumExample) else CurriculumExample.from_dict(item)
            for item in examples
        )
        return tuple(
            sorted(
                normalized,
                key=lambda item: (
                    _stage_rank(self.stage_for_example(item)),
                    -item.evidence_depth,
                    item.example_id,
                ),
            )
        )

    def select_hard_negatives(
        self,
        candidates: Iterable[HardNegativeCandidate | Mapping[str, Any]],
    ) -> HardNegativeSelection:
        normalized = tuple(
            (
                item
                if isinstance(item, HardNegativeCandidate)
                else HardNegativeCandidate.from_dict(item)
            )
            for item in candidates
        )
        decisions: list[HardNegativeDecision] = []
        eligible: list[HardNegativeCandidate] = []

        for candidate in normalized:
            if not candidate.eligible:
                reason = candidate.unresolved_reason or (
                    "hard-negative candidate is missing required evidence metadata"
                    if candidate.evidence_depth is None
                    else f"candidate status is {candidate.status}"
                )
                decisions.append(
                    HardNegativeDecision(
                        candidate_id=candidate.candidate_id,
                        decision="blocked",
                        score=None,
                        reason=reason,
                        candidate=candidate,
                    )
                )
                continue
            eligible.append(candidate)

        eligible_sorted = sorted(
            eligible,
            key=lambda item: (-item.score(), item.candidate_id),
        )
        selected_ids = {
            candidate.candidate_id for candidate in eligible_sorted[: self.hard_negative_limit]
        }

        for candidate in eligible_sorted:
            decision = "selected" if candidate.candidate_id in selected_ids else "blocked"
            reason = (
                "selected as hard negative by evidence depth rank"
                if decision == "selected"
                else "candidate was not selected within the hard-negative limit"
            )
            decisions.append(
                HardNegativeDecision(
                    candidate_id=candidate.candidate_id,
                    decision=decision,
                    score=candidate.score(),
                    reason=reason,
                    candidate=candidate,
                )
            )

        decisions.sort(
            key=lambda item: (
                0 if item.decision == "selected" else 1,
                0 if item.score is None else -item.score,
                item.candidate_id,
            )
        )
        return HardNegativeSelection(decisions=tuple(decisions), limit=self.hard_negative_limit)

    def build_schedule(
        self,
        examples: Iterable[CurriculumExample | Mapping[str, Any]],
        *,
        hard_negative_candidates: Iterable[HardNegativeCandidate | Mapping[str, Any]] = (),
        notes: Iterable[str] = (),
    ) -> CurriculumSchedule:
        ranked_examples = self.rank_examples(examples)
        hard_negatives = self.select_hard_negatives(hard_negative_candidates)
        if any(example.curriculum_state == "mixed" for example in ranked_examples):
            stage = "mixed_transition"
        elif any(example.curriculum_state == "thin" for example in ranked_examples):
            stage = "thin_transition"
        elif any(example.curriculum_state == "progressive" for example in ranked_examples):
            stage = "progressive"
        elif ranked_examples:
            stage = "anchor"
        else:
            stage = "blocked"
        return CurriculumSchedule(
            examples=ranked_examples,
            hard_negatives=hard_negatives,
            stage=stage,
            notes=_dedupe_text(notes),
        )


def build_curriculum_schedule(
    examples: Iterable[CurriculumExample | Mapping[str, Any]],
    *,
    hard_negative_candidates: Iterable[HardNegativeCandidate | Mapping[str, Any]] = (),
    hard_negative_limit: int = 1,
    min_anchor_depth: int = 4,
    min_progressive_depth: int = 2,
    notes: Iterable[str] = (),
) -> CurriculumSchedule:
    return CurriculumScheduler(
        hard_negative_limit=hard_negative_limit,
        min_anchor_depth=min_anchor_depth,
        min_progressive_depth=min_progressive_depth,
    ).build_schedule(
        examples,
        hard_negative_candidates=hard_negative_candidates,
        notes=notes,
    )


__all__ = [
    "CurriculumExample",
    "CurriculumExampleState",
    "CurriculumSchedule",
    "CurriculumScheduler",
    "HardNegativeCandidate",
    "HardNegativeDecision",
    "HardNegativeDecisionState",
    "HardNegativeSelection",
    "build_curriculum_schedule",
]
