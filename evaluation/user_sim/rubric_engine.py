from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from statistics import fmean
from typing import Any, Literal

RubricJudgment = Literal["pass", "weak", "blocked"]
EvidenceMode = Literal["rich", "thin", "mixed", "blocked"]

DEFAULT_USER_SIM_RUBRIC_ID = "phase20-user-sim-rubric:v1"
DEFAULT_TRUTH_BOUNDARY: dict[str, Any] = {
    "prototype_runtime": True,
    "release_grade_corpus_validation": False,
    "weeklong_soak_claim_allowed": False,
    "production_release_claim_allowed": False,
    "full_corpus_validation_allowed": False,
    "partial_packets_allowed": True,
    "thin_lanes_visible": True,
    "power_shell_first": True,
}

_JUDGMENT_BASE: dict[RubricJudgment, tuple[int, int, int]] = {
    "pass": (68, 76, 74),
    "weak": (48, 61, 58),
    "blocked": (32, 82, 50),
}

_EVIDENCE_MODE_ADJUSTMENT: dict[EvidenceMode, tuple[int, int, int]] = {
    "rich": (16, 8, 10),
    "thin": (-14, -10, -10),
    "mixed": (-4, -6, -4),
    "blocked": (-20, -2, -6),
}

_DEPTH_ADJUSTMENT: dict[int, tuple[int, int, int]] = {
    0: (-12, -6, -8),
    1: (-8, -4, -6),
    2: (0, 0, 0),
    3: (3, 2, 2),
    4: (6, 4, 4),
    5: (8, 5, 4),
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (_clean_text(value),)
    if not isinstance(value, Iterable):
        return (_clean_text(value),)
    return tuple(_clean_text(item) for item in value if _clean_text(item))


def _merge_truth_boundary(value: Any) -> dict[str, Any]:
    boundary = dict(DEFAULT_TRUTH_BOUNDARY)
    if value is None:
        return boundary
    if not isinstance(value, Mapping):
        raise TypeError("truth_boundary must be a mapping")
    for key, item in value.items():
        boundary[str(key)] = item
    return boundary


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _mean_or_zero(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    return fmean(float(value) for value in values)


def _normalize_judgment(value: Any) -> RubricJudgment:
    judgment = _clean_text(value).casefold()
    if judgment not in {"pass", "weak", "blocked"}:
        raise ValueError("judgment must be pass, weak, or blocked")
    return judgment  # type: ignore[return-value]


def _normalize_evidence_mode(value: Any) -> EvidenceMode:
    mode = _clean_text(value).casefold()
    if mode not in {"rich", "thin", "mixed", "blocked"}:
        raise ValueError("evidence_mode must be rich, thin, mixed, or blocked")
    return mode  # type: ignore[return-value]


def _claim_text(values: Sequence[str]) -> str:
    return " ".join(value.casefold() for value in values if value)


def _boundary_hits(
    *,
    boundary: Mapping[str, Any],
    claims: Sequence[str],
) -> tuple[str, ...]:
    text = _claim_text(claims)
    if not text:
        return ()

    hits: list[str] = []
    if boundary.get("release_grade_corpus_validation") is False:
        if "release-grade" in text or "release ready" in text or "release-ready" in text:
            hits.append("release-grade claim outside prototype boundary")
    if boundary.get("production_release_claim_allowed") is False:
        if "production-grade" in text or "production equivalent" in text:
            hits.append("production-grade claim outside release boundary")
    if boundary.get("weeklong_soak_claim_allowed") is False:
        if "weeklong soak" in text or "week-long soak" in text or "unattended soak" in text:
            hits.append("weeklong soak claim outside phase 20")
    if boundary.get("full_corpus_validation_allowed") is False:
        if "full corpus" in text or "corpus-scale" in text:
            hits.append("full corpus claim outside frozen cohort")

    ordered: dict[str, str] = {}
    for hit in hits:
        ordered.setdefault(hit, hit)
    return tuple(ordered.values())


@dataclass(frozen=True, slots=True)
class WorkflowRubricScenario:
    scenario_id: str
    persona: str
    judgment: RubricJudgment
    evidence_mode: EvidenceMode
    evidence_depth: int = 0
    truth_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    action_items: tuple[str, ...] = ()
    claims: tuple[str, ...] = ()
    blocker_reason: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _clean_text(self.scenario_id))
        object.__setattr__(self, "persona", _clean_text(self.persona))
        object.__setattr__(self, "judgment", _normalize_judgment(self.judgment))
        object.__setattr__(self, "evidence_mode", _normalize_evidence_mode(self.evidence_mode))
        object.__setattr__(self, "evidence_depth", int(self.evidence_depth))
        object.__setattr__(self, "truth_boundary", _merge_truth_boundary(self.truth_boundary))
        object.__setattr__(self, "evidence_refs", _as_tuple(self.evidence_refs))
        object.__setattr__(self, "action_items", _as_tuple(self.action_items))
        object.__setattr__(self, "claims", _as_tuple(self.claims))
        object.__setattr__(self, "blocker_reason", _clean_text(self.blocker_reason) or None)
        object.__setattr__(self, "notes", _as_tuple(self.notes))

        if not self.scenario_id:
            raise ValueError("scenario_id must not be empty")
        if not self.persona:
            raise ValueError("persona must not be empty")
        if self.evidence_depth < 0:
            raise ValueError("evidence_depth must be non-negative")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WorkflowRubricScenario:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            scenario_id=payload.get("scenario_id") or payload.get("id") or "",
            persona=payload.get("persona") or payload.get("role") or "",
            judgment=payload.get("judgment") or payload.get("outcome") or "weak",
            evidence_mode=payload.get("evidence_mode") or payload.get("evidence_class") or "mixed",
            evidence_depth=int(payload.get("evidence_depth") or 0),
            truth_boundary=payload.get("truth_boundary") or payload.get("boundary") or {},
            evidence_refs=payload.get("evidence_refs") or payload.get("references") or (),
            action_items=payload.get("action_items") or payload.get("next_steps") or (),
            claims=payload.get("claims") or (),
            blocker_reason=payload.get("blocker_reason") or payload.get("reason"),
            notes=payload.get("notes") or payload.get("note") or (),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "persona": self.persona,
            "judgment": self.judgment,
            "evidence_mode": self.evidence_mode,
            "evidence_depth": self.evidence_depth,
            "truth_boundary": dict(self.truth_boundary),
            "evidence_refs": list(self.evidence_refs),
            "action_items": list(self.action_items),
            "claims": list(self.claims),
            "blocker_reason": self.blocker_reason,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class WorkflowRubricScore:
    scenario_id: str
    persona: str
    judgment: RubricJudgment
    evidence_mode: EvidenceMode
    utility_score: int
    trust_score: int
    actionability_score: int
    total_score: int
    evidence_depth: int
    truth_boundary: dict[str, Any]
    boundary_hits: tuple[str, ...]
    rationale: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    action_items: tuple[str, ...] = ()
    claims: tuple[str, ...] = ()
    blocker_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "persona": self.persona,
            "judgment": self.judgment,
            "evidence_mode": self.evidence_mode,
            "utility_score": self.utility_score,
            "trust_score": self.trust_score,
            "actionability_score": self.actionability_score,
            "total_score": self.total_score,
            "evidence_depth": self.evidence_depth,
            "truth_boundary": dict(self.truth_boundary),
            "boundary_hits": list(self.boundary_hits),
            "rationale": list(self.rationale),
            "evidence_refs": list(self.evidence_refs),
            "action_items": list(self.action_items),
            "claims": list(self.claims),
            "blocker_reason": self.blocker_reason,
        }


@dataclass(frozen=True, slots=True)
class WorkflowRubricReport:
    rubric_id: str
    scenario_count: int
    judgment_counts: Mapping[str, int]
    utility_mean: float
    trust_mean: float
    actionability_mean: float
    scores: tuple[WorkflowRubricScore, ...]
    truth_boundary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rubric_id": self.rubric_id,
            "scenario_count": self.scenario_count,
            "judgment_counts": dict(self.judgment_counts),
            "utility_mean": self.utility_mean,
            "trust_mean": self.trust_mean,
            "actionability_mean": self.actionability_mean,
            "scores": [score.to_dict() for score in self.scores],
            "truth_boundary": dict(self.truth_boundary),
        }


@dataclass(frozen=True, slots=True)
class WorkflowRubricEngine:
    rubric_id: str = DEFAULT_USER_SIM_RUBRIC_ID
    truth_boundary: Mapping[str, Any] = field(default_factory=lambda: dict(DEFAULT_TRUTH_BOUNDARY))

    def _score_components(
        self,
        scenario: WorkflowRubricScenario,
    ) -> tuple[int, int, int, tuple[str, ...]]:
        utility, trust, actionability = _JUDGMENT_BASE[scenario.judgment]
        rationale = [
            f"judgment={scenario.judgment}",
            f"evidence_mode={scenario.evidence_mode}",
            f"evidence_depth={scenario.evidence_depth}",
            f"evidence_refs={len(scenario.evidence_refs)}",
            f"action_items={len(scenario.action_items)}",
        ]

        mode_delta = _EVIDENCE_MODE_ADJUSTMENT[scenario.evidence_mode]
        utility += mode_delta[0]
        trust += mode_delta[1]
        actionability += mode_delta[2]

        depth_delta = _DEPTH_ADJUSTMENT.get(scenario.evidence_depth, _DEPTH_ADJUSTMENT[5])
        utility += depth_delta[0]
        trust += depth_delta[1]
        actionability += depth_delta[2]

        reference_bonus = min(4, len(scenario.evidence_refs))
        utility += reference_bonus
        trust += reference_bonus
        actionability += reference_bonus

        action_bonus = min(8, len(scenario.action_items) * 2)
        actionability += action_bonus

        boundary_hits = _boundary_hits(boundary=scenario.truth_boundary, claims=scenario.claims)
        if boundary_hits:
            utility -= 16 * len(boundary_hits)
            trust -= 18 * len(boundary_hits)
            actionability -= 12 * len(boundary_hits)
            rationale.extend(f"boundary_hit={hit}" for hit in boundary_hits)
        else:
            rationale.append("boundary_hits=none")

        if scenario.judgment == "blocked":
            if scenario.blocker_reason:
                trust += 6
                actionability += 8
                rationale.append("blocked judgment preserved with explicit blocker reason")
            else:
                actionability -= 4
                rationale.append("blocked judgment without blocker reason")
        elif scenario.judgment == "weak":
            rationale.append("weak judgment preserved for partial evidence")
        else:
            rationale.append("pass judgment preserved for evidence-rich scenario")

        if scenario.judgment == "pass" and scenario.evidence_mode in {"thin", "blocked"}:
            trust -= 8
            rationale.append("pass judgment on thin or blocked evidence is discounted")

        utility = _clamp_score(utility)
        trust = _clamp_score(trust)
        actionability = _clamp_score(actionability)
        return utility, trust, actionability, tuple(rationale)

    def score_scenario(
        self,
        scenario: WorkflowRubricScenario | Mapping[str, Any],
    ) -> WorkflowRubricScore:
        item = (
            scenario
            if isinstance(scenario, WorkflowRubricScenario)
            else WorkflowRubricScenario.from_dict(scenario)
        )
        merged_boundary = dict(self.truth_boundary)
        merged_boundary.update(item.truth_boundary)
        normalized = WorkflowRubricScenario(
            scenario_id=item.scenario_id,
            persona=item.persona,
            judgment=item.judgment,
            evidence_mode=item.evidence_mode,
            evidence_depth=item.evidence_depth,
            truth_boundary=merged_boundary,
            evidence_refs=item.evidence_refs,
            action_items=item.action_items,
            claims=item.claims,
            blocker_reason=item.blocker_reason,
            notes=item.notes,
        )
        utility, trust, actionability, rationale = self._score_components(normalized)
        total_score = round((utility + trust + actionability) / 3.0)
        return WorkflowRubricScore(
            scenario_id=normalized.scenario_id,
            persona=normalized.persona,
            judgment=normalized.judgment,
            evidence_mode=normalized.evidence_mode,
            utility_score=utility,
            trust_score=trust,
            actionability_score=actionability,
            total_score=total_score,
            evidence_depth=normalized.evidence_depth,
            truth_boundary=dict(normalized.truth_boundary),
            boundary_hits=_boundary_hits(
                boundary=normalized.truth_boundary,
                claims=normalized.claims,
            ),
            rationale=rationale,
            evidence_refs=normalized.evidence_refs,
            action_items=normalized.action_items,
            claims=normalized.claims,
            blocker_reason=normalized.blocker_reason,
        )

    def score_scenarios(
        self,
        scenarios: Iterable[WorkflowRubricScenario | Mapping[str, Any]],
    ) -> WorkflowRubricReport:
        materialized = tuple(self.score_scenario(scenario) for scenario in scenarios)
        if not materialized:
            raise ValueError("scenarios must contain at least one workflow scenario")
        judgment_counts = Counter(score.judgment for score in materialized)
        return WorkflowRubricReport(
            rubric_id=_clean_text(self.rubric_id) or DEFAULT_USER_SIM_RUBRIC_ID,
            scenario_count=len(materialized),
            judgment_counts=dict(judgment_counts),
            utility_mean=_mean_or_zero(tuple(score.utility_score for score in materialized)),
            trust_mean=_mean_or_zero(tuple(score.trust_score for score in materialized)),
            actionability_mean=_mean_or_zero(
                tuple(score.actionability_score for score in materialized)
            ),
            scores=materialized,
            truth_boundary=dict(self.truth_boundary),
        )


def score_workflow_scenario(
    scenario: WorkflowRubricScenario | Mapping[str, Any],
    *,
    rubric_id: str = DEFAULT_USER_SIM_RUBRIC_ID,
    truth_boundary: Mapping[str, Any] | None = None,
) -> WorkflowRubricScore:
    engine = WorkflowRubricEngine(
        rubric_id=rubric_id,
        truth_boundary=dict(truth_boundary or DEFAULT_TRUTH_BOUNDARY),
    )
    return engine.score_scenario(scenario)


def score_workflow_scenarios(
    scenarios: Iterable[WorkflowRubricScenario | Mapping[str, Any]],
    *,
    rubric_id: str = DEFAULT_USER_SIM_RUBRIC_ID,
    truth_boundary: Mapping[str, Any] | None = None,
) -> WorkflowRubricReport:
    engine = WorkflowRubricEngine(
        rubric_id=rubric_id,
        truth_boundary=dict(truth_boundary or DEFAULT_TRUTH_BOUNDARY),
    )
    return engine.score_scenarios(scenarios)


__all__ = [
    "DEFAULT_TRUTH_BOUNDARY",
    "DEFAULT_USER_SIM_RUBRIC_ID",
    "EvidenceMode",
    "RubricJudgment",
    "WorkflowRubricEngine",
    "WorkflowRubricReport",
    "WorkflowRubricScenario",
    "WorkflowRubricScore",
    "score_workflow_scenario",
    "score_workflow_scenarios",
]
