from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

PlausibilityJudgment = Literal["conservative", "weak_usable", "unsupported"]

_BASE_SCORES = {
    "direct_live_smoke": 60,
    "probe_backed": 52,
    "snapshot_backed": 48,
    "verified_accession": 44,
    "mixed_evidence": 40,
    "thin_coverage": 34,
    "blocked": 20,
    "unknown": 24,
}

_EVIDENCE_BOUNDARY_MARKERS = {
    "prototype": "prototype_runtime",
    "partial": "partial_packet",
    "thin": "thin_evidence",
    "mixed": "mixed_evidence",
    "blocked": "blocked",
    "conservative": "conservative_language",
    "provenance": "provenance_language",
    "evidence": "evidence_language",
    "artifact": "artifact_language",
    "checkpoint": "checkpoint_language",
    "trace": "trace_language",
}

_UNSUPPORTED_PATTERNS = (
    ("release_ready_claim", re.compile(r"\brelease[- ]ready\b")),
    ("production_grade_claim", re.compile(r"\bproduction[- ]grade\b")),
    ("fully_validated_claim", re.compile(r"\bfully validated\b")),
    ("complete_corpus_claim", re.compile(r"\bcomplete corpus\b")),
    ("full_corpus_claim", re.compile(r"\bfull corpus\b")),
    ("weeklong_soak_claim", re.compile(r"\bweeklong(?:\s+unattended)?\s+soak\b")),
    ("corpus_scale_claim", re.compile(r"\bcorpus[- ]scale validation\b")),
    ("production_equivalent_claim", re.compile(r"\bproduction[- ]equivalent\b")),
    ("no_blockers_claim", re.compile(r"\bno blockers\b")),
    ("zero_gaps_claim", re.compile(r"\bzero gaps\b")),
    ("all_data_present_claim", re.compile(r"\ball data present\b")),
    ("every_source_mirrored_claim", re.compile(r"\bevery source mirrored\b")),
    ("fully_complete_claim", re.compile(r"\bfully complete\b")),
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", _clean_text(value)).casefold()


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (_clean_text(value),)
    if isinstance(value, Mapping):
        return tuple(_clean_text(item) for item in value.values())
    try:
        return tuple(_clean_text(item) for item in value)
    except TypeError:
        return (_clean_text(value),)


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("truth_boundary must be a mapping")
    return dict(value)


def _mapping_or_attribute(value: Any, *keys: str) -> Any:
    if isinstance(value, Mapping):
        for key in keys:
            if key in value:
                return value[key]
        return None
    for key in keys:
        if hasattr(value, key):
            return getattr(value, key)
    return None


def _is_negated(text: str, start: int) -> bool:
    window = text[max(0, start - 32) : start]
    return bool(
        re.search(r"\b(?:not|no|never|without|n't)\b(?:\W+\w+){0,3}\W*$", window)
    )


def _find_signals(text: str, patterns: tuple[tuple[str, re.Pattern[str]], ...]) -> tuple[str, ...]:
    signals: list[str] = []
    for label, pattern in patterns:
        for match in pattern.finditer(text):
            if _is_negated(text, match.start()):
                continue
            signals.append(label)
            break
    return tuple(signals)


def _normalize_evidence_mode(value: Any) -> str:
    mode = _normalize_text(value)
    if mode in _BASE_SCORES:
        return mode
    if "live" in mode and "smoke" in mode:
        return "direct_live_smoke"
    if "probe" in mode:
        return "probe_backed"
    if "snapshot" in mode:
        return "snapshot_backed"
    if "verified" in mode:
        return "verified_accession"
    if "mixed" in mode:
        return "mixed_evidence"
    if "thin" in mode:
        return "thin_coverage"
    if "blocked" in mode or "unresolved" in mode:
        return "blocked"
    return "unknown"


def _boundary_signals(boundary: Mapping[str, Any], text: str) -> tuple[str, ...]:
    signals: list[str] = []
    normalized = _normalize_text(text)
    for needle, label in _EVIDENCE_BOUNDARY_MARKERS.items():
        if needle in normalized and bool(boundary.get(label, True)):
            signals.append(label)
    return tuple(dict.fromkeys(signals))


def _join_texts(*parts: Any) -> str:
    return " ".join(part for part in (_clean_text(value) for value in parts) if part)


@dataclass(frozen=True, slots=True)
class PlausibilityCase:
    scenario_id: str
    persona: str
    artifact_kind: str
    output_text: str
    evidence_mode: str = "unknown"
    truth_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    claims: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _clean_text(self.scenario_id))
        object.__setattr__(self, "persona", _clean_text(self.persona))
        object.__setattr__(self, "artifact_kind", _clean_text(self.artifact_kind))
        object.__setattr__(self, "output_text", _clean_text(self.output_text))
        object.__setattr__(self, "evidence_mode", _normalize_evidence_mode(self.evidence_mode))
        object.__setattr__(self, "truth_boundary", _coerce_mapping(self.truth_boundary))
        object.__setattr__(self, "evidence_refs", _as_tuple(self.evidence_refs))
        object.__setattr__(self, "claims", _as_tuple(self.claims))
        if not self.scenario_id:
            raise ValueError("scenario_id must not be empty")
        if not self.persona:
            raise ValueError("persona must not be empty")
        if not self.artifact_kind:
            raise ValueError("artifact_kind must not be empty")
        if not self.output_text:
            raise ValueError("output_text must not be empty")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> PlausibilityCase:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            scenario_id=_mapping_or_attribute(payload, "scenario_id", "id") or "",
            persona=_mapping_or_attribute(payload, "persona", "role") or "",
            artifact_kind=_mapping_or_attribute(payload, "artifact_kind", "artifact")
            or "",
            output_text=_mapping_or_attribute(payload, "output_text", "output", "text")
            or "",
            evidence_mode=_mapping_or_attribute(payload, "evidence_mode", "evidence")
            or "unknown",
            truth_boundary=_mapping_or_attribute(payload, "truth_boundary") or {},
            evidence_refs=_mapping_or_attribute(payload, "evidence_refs", "sources") or (),
            claims=_mapping_or_attribute(payload, "claims", "assertions") or (),
        )


@dataclass(frozen=True, slots=True)
class PlausibilityAssessment:
    scenario_id: str
    persona: str
    artifact_kind: str
    evidence_mode: str
    judgment: PlausibilityJudgment
    score: int
    supported_signals: tuple[str, ...]
    unsupported_signals: tuple[str, ...]
    reasons: tuple[str, ...]
    truth_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "persona": self.persona,
            "artifact_kind": self.artifact_kind,
            "evidence_mode": self.evidence_mode,
            "judgment": self.judgment,
            "score": self.score,
            "supported_signals": list(self.supported_signals),
            "unsupported_signals": list(self.unsupported_signals),
            "reasons": list(self.reasons),
            "truth_boundary": dict(self.truth_boundary),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class PlausibilityScorer:
    conservative_threshold: int = 70
    weak_threshold: int = 35

    def score(self, case: PlausibilityCase | Mapping[str, Any]) -> PlausibilityAssessment:
        item = case if isinstance(case, PlausibilityCase) else PlausibilityCase.from_mapping(case)
        output_text = _normalize_text(item.output_text)
        claims_text = _join_texts(*item.claims)
        all_text = _join_texts(output_text, claims_text)
        boundary = dict(item.truth_boundary)
        evidence_mode = _normalize_evidence_mode(item.evidence_mode)
        supported_signals = _find_signals(all_text, _SUPPORTED_PATTERNS)
        unsupported_signals = _find_signals(all_text, _UNSUPPORTED_PATTERNS)
        if unsupported_signals:
            reasons = (
                "unsupported claim detected; fail closed",
                *tuple(f"unsupported_signal={signal}" for signal in unsupported_signals),
                f"evidence_mode={evidence_mode}",
            )
            return PlausibilityAssessment(
                scenario_id=item.scenario_id,
                persona=item.persona,
                artifact_kind=item.artifact_kind,
                evidence_mode=evidence_mode,
                judgment="unsupported",
                score=0,
                supported_signals=supported_signals,
                unsupported_signals=unsupported_signals,
                reasons=reasons,
                truth_boundary=boundary,
                evidence_refs=item.evidence_refs,
            )

        score = _BASE_SCORES[evidence_mode]
        reasons = [f"evidence_mode={evidence_mode}", f"base_score={score}"]
        bonus = 0

        boundary_signals = _boundary_signals(boundary, all_text)
        if boundary_signals:
            bonus += 8
            reasons.append("boundary-aware language detected")
            reasons.extend(f"boundary_signal={signal}" for signal in boundary_signals)

        if item.evidence_refs:
            bonus += 5
            reasons.append("evidence references were provided")

        if supported_signals:
            bonus += 4
            reasons.extend(f"support_signal={signal}" for signal in supported_signals)

        if evidence_mode in {
            "direct_live_smoke",
            "probe_backed",
            "snapshot_backed",
            "verified_accession",
        }:
            bonus += 4
            reasons.append("evidence mode is grounded in real artifacts")

        score = min(100, score + bonus)

        if score >= self.conservative_threshold and evidence_mode != "blocked":
            judgment: PlausibilityJudgment = "conservative"
        elif score >= self.weak_threshold:
            judgment = "weak_usable"
        else:
            judgment = "unsupported"
            score = 0
            reasons.append("score fell below weak threshold")

        return PlausibilityAssessment(
            scenario_id=item.scenario_id,
            persona=item.persona,
            artifact_kind=item.artifact_kind,
            evidence_mode=evidence_mode,
            judgment=judgment,
            score=score,
            supported_signals=supported_signals,
            unsupported_signals=unsupported_signals,
            reasons=tuple(reasons),
            truth_boundary=boundary,
            evidence_refs=item.evidence_refs,
        )


_SUPPORTED_PATTERNS = (
    ("prototype_boundary", re.compile(r"\bprototype boundary\b")),
    ("partiality_acknowledged", re.compile(r"\bpartial\b")),
    ("thin_coverage_acknowledged", re.compile(r"\bthin\b")),
    ("mixed_evidence_acknowledged", re.compile(r"\bmixed(?: evidence)?\b")),
    ("conservative_language", re.compile(r"\bconservative\b")),
    ("provenance_language", re.compile(r"\bprovenance\b")),
    ("evidence_language", re.compile(r"\bevidence\b")),
    ("artifact_language", re.compile(r"\bartifact\b")),
    ("checkpoint_language", re.compile(r"\bcheckpoint\b")),
    ("trace_language", re.compile(r"\btrace\b")),
    ("cannot_claim", re.compile(r"\bcannot claim\b")),
    ("not_release_grade", re.compile(r"\bnot release[- ]grade\b")),
    ("not_complete", re.compile(r"\bnot complete\b")),
)


def score_plausibility(
    case: PlausibilityCase | Mapping[str, Any],
    *,
    scorer: PlausibilityScorer | None = None,
) -> PlausibilityAssessment:
    return (scorer or PlausibilityScorer()).score(case)


__all__ = [
    "PlausibilityAssessment",
    "PlausibilityCase",
    "PlausibilityJudgment",
    "PlausibilityScorer",
    "score_plausibility",
]
