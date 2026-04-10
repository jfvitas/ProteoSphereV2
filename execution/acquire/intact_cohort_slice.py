from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from execution.acquire.intact_snapshot import (
    IntActInteractionRecord,
    IntActSnapshot,
    IntActSnapshotResult,
)
from execution.analysis.cohort_uplift_selector import (
    CohortUpliftCandidate,
    CohortUpliftSelection,
    build_cohort_uplift_selection_from_artifacts,
)

DEFAULT_RESULTS_DIR = Path("runs/real_data_benchmark/full_results")
IntActCohortSliceState = Literal["direct_hit", "reachable_empty", "unavailable"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


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


def _load_selection(results_dir: str | Path) -> CohortUpliftSelection | None:
    root = Path(results_dir)
    try:
        return build_cohort_uplift_selection_from_artifacts(
            root / "usefulness_review.json",
            root / "training_packet_audit.json",
        )
    except (FileNotFoundError, TypeError, ValueError, OSError, KeyError):
        return None


def _selection_candidate(
    accession: str,
    selection: CohortUpliftSelection | None,
) -> tuple[CohortUpliftCandidate | None, int | None]:
    if selection is None:
        return None, None
    for index, candidate in enumerate(selection.candidates, start=1):
        if candidate.accession.casefold() == accession.casefold():
            return candidate, index
    return None, None


def _normalize_snapshot(
    snapshot_result: IntActSnapshotResult | IntActSnapshot | Mapping[str, Any] | None,
) -> tuple[IntActSnapshot | None, str | None]:
    if snapshot_result is None:
        return None, "IntAct snapshot result was not provided"
    if isinstance(snapshot_result, IntActSnapshotResult):
        if not snapshot_result.succeeded or snapshot_result.snapshot is None:
            return None, snapshot_result.reason or "IntAct snapshot acquisition unavailable"
        return snapshot_result.snapshot, snapshot_result.reason
    if isinstance(snapshot_result, IntActSnapshot):
        return snapshot_result, None
    if isinstance(snapshot_result, Mapping):
        normalized = IntActSnapshotResult.from_dict(snapshot_result)
        if not normalized.succeeded or normalized.snapshot is None:
            return None, normalized.reason or "IntAct snapshot acquisition unavailable"
        return normalized.snapshot, normalized.reason
    raise TypeError(
        "snapshot_result must be an IntAct snapshot result, snapshot, "
        "mapping, or None"
    )


def _record_accessions(record: IntActInteractionRecord) -> tuple[str, str]:
    accessions = tuple(
        value
        for value in (
            _clean_text(record.participant_a_primary_id).upper(),
            _clean_text(record.participant_b_primary_id).upper(),
        )
        if value
    )
    if len(accessions) == 2:
        return accessions  # type: ignore[return-value]

    fallback: list[str] = []
    for values in (record.participant_a_ids, record.participant_b_ids):
        for value in values:
            text = _clean_text(value)
            if not text:
                continue
            fallback.append(text.split(":", 1)[-1].strip().upper())
    if len(fallback) < 2:
        raise ValueError("IntAct record does not resolve two accession identifiers")
    return fallback[0], fallback[1]


def _pair_key(accession_a: str, accession_b: str) -> str:
    first, second = sorted((_clean_text(accession_a).upper(), _clean_text(accession_b).upper()))
    if not first or not second:
        raise ValueError("pair key requires two accessions")
    return f"pair:protein_protein:protein:{first}|protein:{second}"


def _record_pointers(record: IntActInteractionRecord, pair_key: str) -> tuple[str, ...]:
    provenance = record.provenance or {}
    pointers = [
        pair_key,
        f"interaction_ac={_clean_text(record.interaction_ac)}",
    ]
    if record.imex_id:
        pointers.append(f"imex_id={record.imex_id}")
    source_release_id = _clean_text(provenance.get("source_release_id"))
    if source_release_id:
        pointers.append(f"source_release_id={source_release_id}")
    source_locator = _clean_text(provenance.get("source_locator"))
    if source_locator:
        pointers.append(source_locator)
    return _dedupe_text(pointers)


def _record_evidence_refs(record: IntActInteractionRecord) -> tuple[str, ...]:
    return _dedupe_text(
        (*record.publication_ids, *record.interaction_ids, *record.confidence_values)
    )


@dataclass(frozen=True, slots=True)
class IntActCohortSlicePair:
    pair_key: str
    accession_pair: tuple[str, str]
    interaction_ac: str | None = None
    imex_id: str | None = None
    lineage_state: str = "participant_only"
    lineage_blockers: tuple[str, ...] = field(default_factory=tuple)
    source_record_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    provenance_pointers: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "pair_key", _clean_text(self.pair_key))
        object.__setattr__(self, "accession_pair", tuple(_dedupe_text(self.accession_pair)))
        object.__setattr__(self, "interaction_ac", _clean_text(self.interaction_ac) or None)
        object.__setattr__(self, "imex_id", _clean_text(self.imex_id) or None)
        object.__setattr__(
            self,
            "lineage_state",
            _clean_text(self.lineage_state) or "participant_only",
        )
        object.__setattr__(self, "lineage_blockers", _dedupe_text(self.lineage_blockers))
        object.__setattr__(self, "source_record_ids", _dedupe_text(self.source_record_ids))
        object.__setattr__(self, "evidence_refs", _dedupe_text(self.evidence_refs))
        object.__setattr__(self, "provenance_pointers", _dedupe_text(self.provenance_pointers))
        if not self.pair_key:
            raise ValueError("pair_key must not be empty")
        if len(self.accession_pair) != 2:
            raise ValueError("accession_pair must contain two accession identifiers")
        lineage_blockers = list(self.lineage_blockers)
        if not self.interaction_ac:
            lineage_blockers.append("missing_interaction_ac")
        if not self.imex_id:
            lineage_blockers.append("missing_imex_id")
        object.__setattr__(self, "lineage_blockers", _dedupe_text(lineage_blockers))
        if self.lineage_blockers:
            if len(self.lineage_blockers) == 1:
                object.__setattr__(self, "lineage_state", "partial_interaction_lineage")
            else:
                object.__setattr__(self, "lineage_state", "participant_only")
        else:
            object.__setattr__(self, "lineage_state", "canonical_interaction")

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_key": self.pair_key,
            "accession_pair": list(self.accession_pair),
            "interaction_ac": self.interaction_ac,
            "imex_id": self.imex_id,
            "lineage_state": self.lineage_state,
            "lineage_blockers": list(self.lineage_blockers),
            "source_record_ids": list(self.source_record_ids),
            "evidence_refs": list(self.evidence_refs),
            "provenance_pointers": list(self.provenance_pointers),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IntActCohortSlicePair:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            pair_key=payload.get("pair_key") or "",
            accession_pair=payload.get("accession_pair") or (),
            interaction_ac=payload.get("interaction_ac"),
            imex_id=payload.get("imex_id"),
            lineage_state=payload.get("lineage_state") or "participant_only",
            lineage_blockers=payload.get("lineage_blockers") or (),
            source_record_ids=payload.get("source_record_ids") or (),
            evidence_refs=payload.get("evidence_refs") or (),
            provenance_pointers=payload.get("provenance_pointers") or (),
        )


@dataclass(frozen=True, slots=True)
class IntActCohortSlice:
    accession: str
    state: IntActCohortSliceState
    pair_records: tuple[IntActCohortSlicePair, ...]
    lineage_state: str = "participant_only"
    lineage_blockers: tuple[str, ...] = field(default_factory=tuple)
    split: str | None = None
    bucket: str | None = None
    canonical_id: str | None = None
    leakage_key: str | None = None
    evidence_mode: str | None = None
    validation_class: str | None = None
    lane_depth: int | None = None
    mixed_evidence: bool | None = None
    thin_coverage: bool | None = None
    priority_class: str | None = None
    priority_score: int | None = None
    selector_rank: int | None = None
    source_lanes: tuple[str, ...] = field(default_factory=tuple)
    present_modalities: tuple[str, ...] = field(default_factory=tuple)
    missing_modalities: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    provenance_pointers: tuple[str, ...] = field(default_factory=tuple)
    probe_reason: str | None = None
    rationale: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _clean_text(self.accession).upper())
        object.__setattr__(
            self,
            "lineage_state",
            _clean_text(self.lineage_state) or "participant_only",
        )
        object.__setattr__(self, "lineage_blockers", _dedupe_text(self.lineage_blockers))
        object.__setattr__(self, "split", _clean_text(self.split) or None)
        object.__setattr__(self, "bucket", _clean_text(self.bucket) or None)
        object.__setattr__(self, "canonical_id", _clean_text(self.canonical_id) or None)
        object.__setattr__(self, "leakage_key", _clean_text(self.leakage_key) or None)
        object.__setattr__(self, "evidence_mode", _clean_text(self.evidence_mode) or None)
        object.__setattr__(self, "validation_class", _clean_text(self.validation_class) or None)
        object.__setattr__(
            self,
            "lane_depth",
            None if self.lane_depth is None else int(self.lane_depth),
        )
        object.__setattr__(
            self,
            "mixed_evidence",
            None if self.mixed_evidence is None else bool(self.mixed_evidence),
        )
        object.__setattr__(
            self,
            "thin_coverage",
            None if self.thin_coverage is None else bool(self.thin_coverage),
        )
        object.__setattr__(self, "priority_class", _clean_text(self.priority_class) or None)
        object.__setattr__(
            self,
            "priority_score",
            None if self.priority_score is None else int(self.priority_score),
        )
        object.__setattr__(
            self,
            "selector_rank",
            None if self.selector_rank is None else int(self.selector_rank),
        )
        object.__setattr__(self, "source_lanes", _dedupe_text(self.source_lanes))
        object.__setattr__(self, "present_modalities", _dedupe_text(self.present_modalities))
        object.__setattr__(self, "missing_modalities", _dedupe_text(self.missing_modalities))
        object.__setattr__(self, "evidence_refs", _dedupe_text(self.evidence_refs))
        object.__setattr__(self, "provenance_pointers", _dedupe_text(self.provenance_pointers))
        object.__setattr__(self, "probe_reason", _clean_text(self.probe_reason) or None)
        object.__setattr__(self, "rationale", _dedupe_text(self.rationale))
        pairs: list[IntActCohortSlicePair] = []
        seen: set[str] = set()
        for pair in self.pair_records:
            if not isinstance(pair, IntActCohortSlicePair):
                raise TypeError("pair_records must contain IntActCohortSlicePair objects")
            if pair.pair_key in seen:
                continue
            seen.add(pair.pair_key)
            pairs.append(pair)
        object.__setattr__(
            self,
            "pair_records",
            tuple(sorted(pairs, key=lambda pair: pair.pair_key)),
        )
        if self.pair_records:
            blockers = [blocker for pair in self.pair_records for blocker in pair.lineage_blockers]
            object.__setattr__(self, "lineage_blockers", _dedupe_text(blockers))
            if not self.lineage_blockers:
                object.__setattr__(self, "lineage_state", "canonical_interaction")
            elif len(self.lineage_blockers) == 1:
                object.__setattr__(self, "lineage_state", "partial_interaction_lineage")
            else:
                object.__setattr__(self, "lineage_state", "participant_only")
        elif self.state == "reachable_empty":
            object.__setattr__(self, "lineage_blockers", ("no_curated_intact_pairs",))
            object.__setattr__(self, "lineage_state", "participant_only")
        elif self.state == "unavailable":
            object.__setattr__(self, "lineage_blockers", ("intact_snapshot_unavailable",))
            object.__setattr__(self, "lineage_state", "participant_only")
        if self.state not in {"direct_hit", "reachable_empty", "unavailable"}:
            raise ValueError(f"unsupported state: {self.state!r}")
        if not self.accession:
            raise ValueError("accession must not be empty")

    @property
    def pair_count(self) -> int:
        return len(self.pair_records)

    @property
    def pair_keys(self) -> tuple[str, ...]:
        return tuple(pair.pair_key for pair in self.pair_records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "state": self.state,
            "lineage_state": self.lineage_state,
            "lineage_blockers": list(self.lineage_blockers),
            "pair_count": self.pair_count,
            "pair_keys": list(self.pair_keys),
            "pair_records": [pair.to_dict() for pair in self.pair_records],
            "split": self.split,
            "bucket": self.bucket,
            "canonical_id": self.canonical_id,
            "leakage_key": self.leakage_key,
            "evidence_mode": self.evidence_mode,
            "validation_class": self.validation_class,
            "lane_depth": self.lane_depth,
            "mixed_evidence": self.mixed_evidence,
            "thin_coverage": self.thin_coverage,
            "priority_class": self.priority_class,
            "priority_score": self.priority_score,
            "selector_rank": self.selector_rank,
            "source_lanes": list(self.source_lanes),
            "present_modalities": list(self.present_modalities),
            "missing_modalities": list(self.missing_modalities),
            "evidence_refs": list(self.evidence_refs),
            "provenance_pointers": list(self.provenance_pointers),
            "probe_reason": self.probe_reason,
            "rationale": list(self.rationale),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IntActCohortSlice:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            accession=payload.get("accession") or "",
            state=payload.get("state") or "unavailable",
            lineage_state=payload.get("lineage_state") or "participant_only",
            lineage_blockers=payload.get("lineage_blockers") or (),
            pair_records=tuple(
                item
                if isinstance(item, IntActCohortSlicePair)
                else IntActCohortSlicePair.from_dict(item)
                for item in _iter_values(payload.get("pair_records") or payload.get("pairs") or ())
            ),
            split=payload.get("split"),
            bucket=payload.get("bucket"),
            canonical_id=payload.get("canonical_id"),
            leakage_key=payload.get("leakage_key"),
            evidence_mode=payload.get("evidence_mode"),
            validation_class=payload.get("validation_class"),
            lane_depth=payload.get("lane_depth"),
            mixed_evidence=payload.get("mixed_evidence"),
            thin_coverage=payload.get("thin_coverage"),
            priority_class=payload.get("priority_class"),
            priority_score=payload.get("priority_score"),
            selector_rank=payload.get("selector_rank"),
            source_lanes=payload.get("source_lanes") or (),
            present_modalities=payload.get("present_modalities") or (),
            missing_modalities=payload.get("missing_modalities") or (),
            evidence_refs=payload.get("evidence_refs") or (),
            provenance_pointers=payload.get("provenance_pointers") or (),
            probe_reason=payload.get("probe_reason") or payload.get("reason"),
            rationale=payload.get("rationale") or (),
        )


def _record_to_pair(record: IntActInteractionRecord) -> IntActCohortSlicePair:
    accession_a, accession_b = _record_accessions(record)
    pair_key = _pair_key(accession_a, accession_b)
    provenance = record.provenance or {}
    provenance_pointers = [
        pair_key,
        f"interaction_ac={_clean_text(record.interaction_ac)}",
    ]
    if record.imex_id:
        provenance_pointers.append(f"imex_id={record.imex_id}")
    source_release_id = _clean_text(provenance.get("source_release_id"))
    if source_release_id:
        provenance_pointers.append(f"source_release_id={source_release_id}")
    source_locator = _clean_text(provenance.get("source_locator"))
    if source_locator:
        provenance_pointers.append(source_locator)
    source_record_ids = _dedupe_text((record.interaction_ac, record.imex_id))
    if not source_record_ids:
        source_record_ids = _dedupe_text(record.interaction_ids)
    return IntActCohortSlicePair(
        pair_key=pair_key,
        accession_pair=tuple(sorted((accession_a, accession_b))),
        interaction_ac=_clean_text(record.interaction_ac) or None,
        imex_id=_clean_text(record.imex_id) or None,
        lineage_state=_clean_text(record.lineage_state) or "participant_only",
        lineage_blockers=record.lineage_blockers,
        source_record_ids=source_record_ids,
        evidence_refs=_record_evidence_refs(record),
        provenance_pointers=_dedupe_text(provenance_pointers),
    )


def _lookup_pair_candidate(
    accession: str,
    selection: CohortUpliftSelection | None,
) -> tuple[CohortUpliftCandidate | None, int | None]:
    if selection is None:
        return None, None
    for index, candidate in enumerate(selection.candidates, start=1):
        if candidate.accession.casefold() == accession.casefold():
            return candidate, index
    return None, None


def materialize_intact_cohort_slice(
    accession: str,
    *,
    snapshot_result: IntActSnapshotResult | IntActSnapshot | Mapping[str, Any] | None = None,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
    selection: CohortUpliftSelection | None = None,
) -> IntActCohortSlice:
    normalized_accession = _clean_text(accession).upper()
    if not normalized_accession:
        raise ValueError("accession must not be empty")

    candidate, selector_rank = _lookup_pair_candidate(
        normalized_accession,
        selection or _load_selection(results_dir),
    )
    snapshot, reason = _normalize_snapshot(snapshot_result)

    if snapshot is None:
        return IntActCohortSlice(
            accession=normalized_accession,
            state="unavailable",
            pair_records=(),
            split=candidate.split if candidate else None,
            canonical_id=candidate.canonical_id if candidate else None,
            leakage_key=normalized_accession,
            evidence_mode=candidate.evidence_mode if candidate else None,
            validation_class=candidate.validation_class if candidate else None,
            lane_depth=candidate.lane_depth if candidate else None,
            mixed_evidence=candidate.mixed_evidence if candidate else None,
            thin_coverage=candidate.thin_coverage if candidate else None,
            priority_class=candidate.priority_class if candidate else None,
            priority_score=candidate.priority_score if candidate else None,
            selector_rank=selector_rank,
            source_lanes=tuple(candidate.source_lanes) if candidate else (),
            present_modalities=tuple(candidate.present_modalities) if candidate else (),
            missing_modalities=tuple(candidate.missing_modalities) if candidate else (),
            evidence_refs=(),
            provenance_pointers=_dedupe_text(
                (
                    f"selector_rank={selector_rank}" if selector_rank is not None else "",
                    f"selector_priority={candidate.priority_class}" if candidate else "",
                    reason or "",
                )
            ),
            probe_reason=reason,
            rationale=tuple(candidate.rationale) if candidate else (),
        )

    matched = [
        record
        for record in snapshot.records
        if normalized_accession.casefold()
        in {item.casefold() for item in _record_accessions(record)}
    ]
    pair_map: dict[str, IntActCohortSlicePair] = {}
    for record in matched:
        try:
            pair = _record_to_pair(record)
        except ValueError:
            continue
        existing = pair_map.get(pair.pair_key)
        if existing is None:
            pair_map[pair.pair_key] = pair
            continue
        pair_map[pair.pair_key] = IntActCohortSlicePair(
            pair_key=existing.pair_key,
            accession_pair=existing.accession_pair,
            source_record_ids=tuple((*existing.source_record_ids, *pair.source_record_ids)),
            evidence_refs=tuple((*existing.evidence_refs, *pair.evidence_refs)),
            provenance_pointers=tuple(
                (*existing.provenance_pointers, *pair.provenance_pointers)
            ),
        )

    state: IntActCohortSliceState = "direct_hit" if pair_map else "reachable_empty"
    probe_reason = (
        "direct curated pair evidence located"
        if pair_map
        else "IntAct probe succeeded but no curated IntAct pairs were returned"
    )
    provenance_pointers = [
        f"selector_rank={selector_rank}" if selector_rank is not None else "",
        f"selector_priority={candidate.priority_class}" if candidate else "",
        f"selector_score={candidate.priority_score}" if candidate else "",
    ]
    if candidate and candidate.planning_index_ref:
        provenance_pointers.append(candidate.planning_index_ref)
    provenance = snapshot.provenance.to_dict()
    source_release_id = _clean_text(provenance.get("source_release_id"))
    if source_release_id:
        provenance_pointers.append(f"source_release_id={source_release_id}")
    source_locator = _clean_text(provenance.get("source_locator"))
    if source_locator:
        provenance_pointers.append(source_locator)
    provenance_pointers.append(f"record_count={len(snapshot.records)}")

    return IntActCohortSlice(
        accession=normalized_accession,
        state=state,
        pair_records=tuple(
            sorted(pair_map.values(), key=lambda pair: pair.pair_key.casefold())
        ),
        split=candidate.split if candidate else None,
        canonical_id=candidate.canonical_id if candidate else None,
        leakage_key=normalized_accession,
        evidence_mode=candidate.evidence_mode if candidate else None,
        validation_class=candidate.validation_class if candidate else None,
        lane_depth=candidate.lane_depth if candidate else None,
        mixed_evidence=candidate.mixed_evidence if candidate else None,
        thin_coverage=candidate.thin_coverage if candidate else None,
        priority_class=candidate.priority_class if candidate else None,
        priority_score=candidate.priority_score if candidate else None,
        selector_rank=selector_rank,
        source_lanes=tuple(candidate.source_lanes) if candidate else (),
        present_modalities=tuple(candidate.present_modalities) if candidate else (),
        missing_modalities=tuple(candidate.missing_modalities) if candidate else (),
        evidence_refs=tuple(
            dict.fromkeys(
                ref
                for pair in pair_map.values()
                for ref in pair.evidence_refs
            )
        ),
        provenance_pointers=_dedupe_text(provenance_pointers),
        probe_reason=probe_reason,
        rationale=(tuple(candidate.rationale) if candidate else ()) + (probe_reason,),
    )


def materialize_intact_cohort_slice_from_artifacts(
    accession: str,
    *,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
    snapshot_result: IntActSnapshotResult | IntActSnapshot | Mapping[str, Any] | None = None,
) -> IntActCohortSlice:
    return materialize_intact_cohort_slice(
        accession,
        snapshot_result=snapshot_result,
        results_dir=results_dir,
    )


__all__ = [
    "DEFAULT_RESULTS_DIR",
    "IntActCohortSlice",
    "IntActCohortSlicePair",
    "IntActCohortSliceState",
    "materialize_intact_cohort_slice",
    "materialize_intact_cohort_slice_from_artifacts",
]
