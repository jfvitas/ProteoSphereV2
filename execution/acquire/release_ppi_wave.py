from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

PPISourceTier = Literal["direct", "breadth"]
PPISourceDecisionStatus = Literal["observed", "missing"]
PPIWaveCaseKind = Literal[
    "direct_single_source",
    "breadth_only",
    "multi_source",
    "unresolved",
]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        iterable: Sequence[Any] = (values,)
    elif isinstance(values, Sequence):
        iterable = values
    else:
        iterable = (values,)
    ordered: dict[str, str] = {}
    for value in iterable:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _load_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, Path):
        return json.loads(value.read_text(encoding="utf-8"))
    if isinstance(value, str):
        path = Path(value)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return json.loads(value)
    return value


def _row_iter(payload: Any) -> tuple[Mapping[str, Any], ...]:
    value = _load_payload(payload)
    if isinstance(value, Mapping):
        for key in ("cohort", "coverage_matrix", "rows", "entries"):
            rows = value.get(key)
            if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
                return tuple(row for row in rows if isinstance(row, Mapping))
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(row for row in value if isinstance(row, Mapping))
    raise TypeError("cohort payload must be a mapping or a sequence of mappings")


@dataclass(frozen=True, slots=True)
class PPISourceSpec:
    source_name: str
    source_tier: PPISourceTier
    release_rank: int
    release_role: str
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "source_tier", _clean_text(self.source_tier))
        object.__setattr__(self, "release_rank", int(self.release_rank))
        object.__setattr__(self, "release_role", _clean_text(self.release_role))
        object.__setattr__(self, "notes", _clean_text(self.notes))
        if not self.source_name:
            raise ValueError("source_name must not be empty")
        if self.source_tier not in {"direct", "breadth"}:
            raise ValueError("source_tier must be direct or breadth")
        if self.release_rank < 1:
            raise ValueError("release_rank must be positive")
        if not self.release_role:
            raise ValueError("release_role must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_tier": self.source_tier,
            "release_rank": self.release_rank,
            "release_role": self.release_role,
            "notes": self.notes,
        }


DEFAULT_PPI_SOURCE_SPECS: tuple[PPISourceSpec, ...] = (
    PPISourceSpec(
        source_name="IntAct",
        source_tier="direct",
        release_rank=1,
        release_role="curated direct interaction evidence",
    ),
    PPISourceSpec(
        source_name="BioGRID",
        source_tier="direct",
        release_rank=2,
        release_role="curated direct interaction breadth",
    ),
    PPISourceSpec(
        source_name="STRING",
        source_tier="breadth",
        release_rank=3,
        release_role="breadth support only",
        notes="contextual breadth lane; do not treat as curated direct evidence",
    ),
)


@dataclass(frozen=True, slots=True)
class PPISourceDecision:
    source_name: str
    source_tier: PPISourceTier
    release_rank: int
    status: PPISourceDecisionStatus

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "source_tier", _clean_text(self.source_tier))
        object.__setattr__(self, "release_rank", int(self.release_rank))
        object.__setattr__(self, "status", _clean_text(self.status))
        if not self.source_name:
            raise ValueError("source_name must not be empty")
        if self.source_tier not in {"direct", "breadth"}:
            raise ValueError("source_tier must be direct or breadth")
        if self.release_rank < 1:
            raise ValueError("release_rank must be positive")
        if self.status not in {"observed", "missing"}:
            raise ValueError("status must be observed or missing")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_tier": self.source_tier,
            "release_rank": self.release_rank,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ReleasePPIWaveRecord:
    accession: str
    split: str = ""
    bucket: str = ""
    evidence_mode: str = ""
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    source_lanes: tuple[str, ...] = field(default_factory=tuple)
    source_decisions: tuple[PPISourceDecision, ...] = field(default_factory=tuple)
    observed_sources: tuple[str, ...] = field(default_factory=tuple)
    next_sources: tuple[str, ...] = field(default_factory=tuple)
    unsupported_lanes: tuple[str, ...] = field(default_factory=tuple)
    primary_observed_source: str = ""
    case_kind: PPIWaveCaseKind = "unresolved"
    multi_source: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _clean_text(self.accession))
        object.__setattr__(self, "split", _clean_text(self.split))
        object.__setattr__(self, "bucket", _clean_text(self.bucket))
        object.__setattr__(self, "evidence_mode", _clean_text(self.evidence_mode))
        object.__setattr__(self, "evidence_refs", _clean_text_tuple(self.evidence_refs))
        object.__setattr__(self, "source_lanes", _clean_text_tuple(self.source_lanes))
        object.__setattr__(self, "source_decisions", tuple(self.source_decisions))
        object.__setattr__(self, "observed_sources", _clean_text_tuple(self.observed_sources))
        object.__setattr__(self, "next_sources", _clean_text_tuple(self.next_sources))
        object.__setattr__(self, "unsupported_lanes", _clean_text_tuple(self.unsupported_lanes))
        object.__setattr__(
            self,
            "primary_observed_source",
            _clean_text(self.primary_observed_source),
        )
        object.__setattr__(self, "case_kind", _clean_text(self.case_kind))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        object.__setattr__(self, "multi_source", bool(self.multi_source))
        if not self.accession:
            raise ValueError("accession must not be empty")
        if self.case_kind not in {
            "direct_single_source",
            "breadth_only",
            "multi_source",
            "unresolved",
        }:
            raise ValueError("invalid case_kind")

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "split": self.split,
            "bucket": self.bucket,
            "evidence_mode": self.evidence_mode,
            "evidence_refs": list(self.evidence_refs),
            "source_lanes": list(self.source_lanes),
            "source_decisions": [decision.to_dict() for decision in self.source_decisions],
            "observed_sources": list(self.observed_sources),
            "next_sources": list(self.next_sources),
            "unsupported_lanes": list(self.unsupported_lanes),
            "primary_observed_source": self.primary_observed_source,
            "case_kind": self.case_kind,
            "multi_source": self.multi_source,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ReleasePPIWavePlan:
    plan_id: str
    manifest_id: str
    source_ranking: tuple[PPISourceSpec, ...]
    records: tuple[ReleasePPIWaveRecord, ...]
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "manifest_id": self.manifest_id,
            "source_ranking": [spec.to_dict() for spec in self.source_ranking],
            "records": [record.to_dict() for record in self.records],
            "summary": dict(self.summary),
        }


def _source_spec_index(
    source_specs: Sequence[PPISourceSpec],
) -> dict[str, PPISourceSpec]:
    return {spec.source_name.casefold(): spec for spec in source_specs}


def _classify_record(
    row: Mapping[str, Any],
    source_specs: Sequence[PPISourceSpec],
) -> ReleasePPIWaveRecord:
    spec_index = _source_spec_index(source_specs)
    lanes = _clean_text_tuple(
        row.get("source_lanes")
        or row.get("source_lane")
        or row.get("source")
        or (),
    )
    evidence_refs = _clean_text_tuple(row.get("evidence_refs") or row.get("evidence_ref") or ())
    lanes_casefold = {lane.casefold() for lane in lanes}
    observed_sources = tuple(
        spec.source_name
        for spec in source_specs
        if spec.source_name.casefold() in lanes_casefold
    )
    decisions = tuple(
        PPISourceDecision(
            source_name=spec.source_name,
            source_tier=spec.source_tier,
            release_rank=spec.release_rank,
            status="observed" if spec.source_name in observed_sources else "missing",
        )
        for spec in source_specs
    )
    unsupported_lanes = tuple(
        lane
        for lane in lanes
        if lane.casefold() not in spec_index
    )
    direct_observed = tuple(
        spec.source_name
        for spec in source_specs
        if spec.source_tier == "direct" and spec.source_name in observed_sources
    )
    breadth_observed = tuple(
        spec.source_name
        for spec in source_specs
        if spec.source_tier == "breadth" and spec.source_name in observed_sources
    )
    next_sources = tuple(
        spec.source_name
        for spec in source_specs
        if spec.source_name not in observed_sources
    )
    if len(observed_sources) > 1:
        case_kind: PPIWaveCaseKind = "multi_source"
    elif direct_observed:
        case_kind = "direct_single_source"
    elif breadth_observed:
        case_kind = "breadth_only"
    else:
        case_kind = "unresolved"
    notes: list[str] = []
    if unsupported_lanes:
        notes.append("unsupported_lanes_preserved")
    if case_kind == "multi_source":
        notes.append("multi_source_case_explicit")
    if case_kind == "unresolved":
        notes.append("ppi_sources_unresolved")
    if direct_observed:
        notes.append("direct_ppi_source_observed")
    if breadth_observed:
        notes.append("breadth_ppi_source_observed")
    primary_observed_source = observed_sources[0] if observed_sources else ""
    return ReleasePPIWaveRecord(
        accession=_clean_text(row.get("accession")),
        split=_clean_text(row.get("split")),
        bucket=_clean_text(row.get("bucket")),
        evidence_mode=_clean_text(row.get("evidence_mode")),
        evidence_refs=evidence_refs,
        source_lanes=lanes,
        source_decisions=decisions,
        observed_sources=observed_sources,
        next_sources=next_sources,
        unsupported_lanes=unsupported_lanes,
        primary_observed_source=primary_observed_source,
        case_kind=case_kind,
        multi_source=len(observed_sources) > 1,
        notes=tuple(notes),
    )


def _plan_id_with_specs(
    manifest_id: str,
    records: Sequence[ReleasePPIWaveRecord],
    source_specs: Sequence[PPISourceSpec],
) -> str:
    digest_source = {
        "manifest_id": manifest_id,
        "records": [record.to_dict() for record in records],
        "source_ranking": [spec.to_dict() for spec in source_specs],
    }
    digest = sha256(
        json.dumps(digest_source, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"release-ppi-wave-{digest[:16]}"


def build_release_ppi_wave_plan(
    cohort: Any,
    *,
    source_specs: Sequence[PPISourceSpec] = DEFAULT_PPI_SOURCE_SPECS,
) -> ReleasePPIWavePlan:
    payload = _load_payload(cohort)
    manifest_id = ""
    rows: tuple[Mapping[str, Any], ...]
    if isinstance(payload, Mapping):
        manifest_id = _clean_text(payload.get("manifest_id") or payload.get("cohort_manifest_id"))
        rows = _row_iter(payload)
    else:
        rows = _row_iter(payload)
    records = tuple(_classify_record(row, source_specs) for row in rows)
    plan_id = _plan_id_with_specs(manifest_id, records, source_specs)
    direct_covered_accessions = sum(
        1
        for record in records
        if record.observed_sources and record.case_kind in {
            "direct_single_source",
            "multi_source",
        }
    )
    breadth_covered_accessions = sum(
        1
        for record in records
        if record.case_kind in {"breadth_only", "multi_source"}
    )
    summary = {
        "total_accessions": len(records),
        "direct_covered_accessions": direct_covered_accessions,
        "breadth_covered_accessions": breadth_covered_accessions,
        "multi_source_accessions": sum(1 for record in records if record.multi_source),
        "unresolved_accessions": sum(1 for record in records if record.case_kind == "unresolved"),
        "unsupported_lane_accessions": sum(1 for record in records if record.unsupported_lanes),
    }
    return ReleasePPIWavePlan(
        plan_id=plan_id,
        manifest_id=manifest_id,
        source_ranking=tuple(source_specs),
        records=records,
        summary=summary,
    )
