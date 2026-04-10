from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from execution.acquire.evolutionary_snapshot import (
    EvolutionarySnapshot,
    EvolutionarySnapshotRecord,
    EvolutionarySnapshotResult,
)

EvolutionaryPacketLaneState = Literal["positive_hit", "unresolved", "blocked"]


class EvolutionaryPacketLaneError(ValueError):
    """Raised when an evolutionary packet lane payload cannot be normalized."""


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise EvolutionaryPacketLaneError(f"{field_name} must be a non-empty string")
    return text


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Sequence):
        return tuple(values)
    return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _normalize_accession(value: Any) -> str:
    accession = _clean_text(value).upper()
    if not accession:
        return ""
    if not 6 <= len(accession) <= 10 or not accession.isalnum():
        return ""
    return accession


def _coerce_accessions(values: Any) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        accession = _normalize_accession(value)
        if not accession or accession in seen:
            continue
        seen.add(accession)
        normalized.append(accession)
    return tuple(normalized)


def _record_accession(record: Any) -> str:
    accession = _normalize_accession(
        _record_value(record, "accession")
        or _record_value(record, "uniprot_accession")
        or _record_value(record, "uniprot_id")
        or _record_value(record, "primary_accession")
    )
    if not accession:
        raise EvolutionaryPacketLaneError("record is missing a valid accession")
    return accession


def _record_value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _record_int(record: Any, key: str) -> int | None:
    value = _record_value(record, key)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise EvolutionaryPacketLaneError(f"{key} must be an integer") from exc


def _record_float(record: Any, key: str) -> float | None:
    value = _record_value(record, key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise EvolutionaryPacketLaneError(f"{key} must be numeric") from exc


def _record_fields(record: Any) -> dict[str, Any]:
    if isinstance(record, EvolutionarySnapshotRecord):
        return record.metadata
    if isinstance(record, Mapping):
        return dict(record)
    fields: dict[str, Any] = {}
    for key in (
        "sequence_version",
        "sequence_hash",
        "sequence_length",
        "taxon_id",
        "uniref_cluster_ids",
        "orthogroup_ids",
        "alignment_depth",
        "alignment_coverage",
        "neff",
        "gap_fraction",
        "quality_flags",
        "source_refs",
        "lazy_materialization_refs",
        "metadata",
    ):
        value = _record_value(record, key)
        if value is not None:
            fields[key] = value
    return fields


def _snapshot_status(result: Any) -> str:
    return _clean_text(_result_value(result, "status")).casefold()


def _result_value(result: Any, key: str, default: Any = None) -> Any:
    if isinstance(result, Mapping):
        return result.get(key, default)
    return getattr(result, key, default)


def _snapshot_records(result: Any) -> tuple[Any, ...]:
    snapshot = _result_value(result, "snapshot")
    if snapshot is None:
        return ()
    if isinstance(snapshot, EvolutionarySnapshot):
        return snapshot.records
    if isinstance(snapshot, Mapping):
        records = snapshot.get("records") or snapshot.get("items") or snapshot.get("entries")
        if records is None and isinstance(snapshot, Mapping):
            records = snapshot
        return tuple(_iter_values(records))
    records = getattr(snapshot, "records", ())
    return tuple(_iter_values(records))


def _snapshot_manifest(result: Any) -> Mapping[str, Any]:
    manifest = _result_value(result, "manifest")
    if isinstance(manifest, Mapping):
        return manifest
    to_dict = getattr(manifest, "to_dict", None)
    if callable(to_dict):
        payload = to_dict()
        if isinstance(payload, Mapping):
            return payload
    return {}


def _snapshot_provenance(result: Any) -> Mapping[str, Any]:
    provenance = _result_value(result, "provenance")
    if isinstance(provenance, Mapping):
        return provenance
    if provenance is None:
        return {}
    to_dict = getattr(provenance, "to_dict", None)
    if callable(to_dict):
        payload = to_dict()
        if isinstance(payload, Mapping):
            return payload
    return {}


def _mapping_text(mapping: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        text = _clean_text(value)
        if text:
            return text
    return default


@dataclass(frozen=True, slots=True)
class EvolutionaryPacketLaneEntry:
    accession: str
    lane_state: EvolutionaryPacketLaneState
    lane_depth: int
    corpus_snapshot_id: str | None = None
    aligner_version: str | None = None
    source_layers: tuple[str, ...] = ()
    sequence_version: str | None = None
    sequence_hash: str | None = None
    sequence_length: int | None = None
    taxon_id: int | None = None
    alignment_depth: int | None = None
    alignment_coverage: float | None = None
    neff: float | None = None
    gap_fraction: float | None = None
    uniref_cluster_ids: tuple[str, ...] = ()
    orthogroup_ids: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    lazy_materialization_refs: tuple[str, ...] = ()
    blocker_reason: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        accession = _normalize_accession(self.accession)
        if not accession:
            raise EvolutionaryPacketLaneError("accession must be a valid UniProt accession")
        lane_state = _clean_text(self.lane_state).casefold()
        if lane_state not in {"positive_hit", "unresolved", "blocked"}:
            raise EvolutionaryPacketLaneError("lane_state must describe an evolutionary lane")
        if self.lane_depth < 0:
            raise EvolutionaryPacketLaneError("lane_depth must be non-negative")
        if self.sequence_length is not None and self.sequence_length < 0:
            raise EvolutionaryPacketLaneError("sequence_length must be non-negative")
        if self.taxon_id is not None and self.taxon_id < 0:
            raise EvolutionaryPacketLaneError("taxon_id must be non-negative")
        for field_name, value in (
            ("alignment_depth", self.alignment_depth),
            ("alignment_coverage", self.alignment_coverage),
            ("neff", self.neff),
            ("gap_fraction", self.gap_fraction),
        ):
            if field_name != "alignment_coverage" and value is not None and value < 0:
                raise EvolutionaryPacketLaneError(f"{field_name} must be non-negative")
            if field_name == "alignment_coverage" and value is not None and not 0 <= value <= 1:
                raise EvolutionaryPacketLaneError("alignment_coverage must be between 0 and 1")

        object.__setattr__(self, "accession", accession)
        object.__setattr__(self, "lane_state", lane_state)
        object.__setattr__(self, "source_layers", _dedupe_text(self.source_layers))
        object.__setattr__(self, "sequence_version", _clean_text(self.sequence_version) or None)
        object.__setattr__(self, "sequence_hash", _clean_text(self.sequence_hash) or None)
        object.__setattr__(self, "uniref_cluster_ids", _dedupe_text(self.uniref_cluster_ids))
        object.__setattr__(self, "orthogroup_ids", _dedupe_text(self.orthogroup_ids))
        object.__setattr__(self, "quality_flags", _dedupe_text(self.quality_flags))
        object.__setattr__(self, "source_refs", _dedupe_text(self.source_refs))
        object.__setattr__(
            self,
            "lazy_materialization_refs",
            _dedupe_text(self.lazy_materialization_refs),
        )
        object.__setattr__(self, "blocker_reason", _clean_text(self.blocker_reason) or None)
        object.__setattr__(self, "notes", _dedupe_text(self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "lane_state": self.lane_state,
            "lane_depth": self.lane_depth,
            "corpus_snapshot_id": self.corpus_snapshot_id,
            "aligner_version": self.aligner_version,
            "source_layers": list(self.source_layers),
            "sequence_version": self.sequence_version,
            "sequence_hash": self.sequence_hash,
            "sequence_length": self.sequence_length,
            "taxon_id": self.taxon_id,
            "alignment_depth": self.alignment_depth,
            "alignment_coverage": self.alignment_coverage,
            "neff": self.neff,
            "gap_fraction": self.gap_fraction,
            "uniref_cluster_ids": list(self.uniref_cluster_ids),
            "orthogroup_ids": list(self.orthogroup_ids),
            "quality_flags": list(self.quality_flags),
            "source_refs": list(self.source_refs),
            "lazy_materialization_refs": list(self.lazy_materialization_refs),
            "blocker_reason": self.blocker_reason,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class EvolutionaryPacketLaneResult:
    cohort_accessions: tuple[str, ...]
    packet_lanes: tuple[EvolutionaryPacketLaneEntry, ...]
    positive_accessions: tuple[str, ...]
    unresolved_accessions: tuple[str, ...]
    blocked_accessions: tuple[str, ...]
    snapshot_status: str
    snapshot_reason: str | None = None
    snapshot_record_count: int = 0
    source_snapshot_id: str | None = None
    aligner_version: str | None = None
    source_layers: tuple[str, ...] = ()
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cohort_accessions": list(self.cohort_accessions),
            "packet_lanes": [lane.to_dict() for lane in self.packet_lanes],
            "positive_accessions": list(self.positive_accessions),
            "unresolved_accessions": list(self.unresolved_accessions),
            "blocked_accessions": list(self.blocked_accessions),
            "snapshot_status": self.snapshot_status,
            "snapshot_reason": self.snapshot_reason,
            "snapshot_record_count": self.snapshot_record_count,
            "source_snapshot_id": self.source_snapshot_id,
            "aligner_version": self.aligner_version,
            "source_layers": list(self.source_layers),
            "summary": dict(self.summary),
        }


def build_evolutionary_packet_lane(
    cohort_accessions: Sequence[str] | str,
    *,
    snapshot_result: EvolutionarySnapshotResult | Mapping[str, Any] | None = None,
) -> EvolutionaryPacketLaneResult:
    normalized_accessions = _coerce_accessions(cohort_accessions)
    snapshot_status = (
        _snapshot_status(snapshot_result) if snapshot_result is not None else "missing"
    )
    snapshot_reason = (
        _clean_text(_result_value(snapshot_result, "reason")) if snapshot_result else ""
    )
    manifest = _snapshot_manifest(snapshot_result) if snapshot_result is not None else {}
    provenance = _snapshot_provenance(snapshot_result) if snapshot_result is not None else {}
    records = _snapshot_records(snapshot_result) if snapshot_result is not None else ()
    records_by_accession: dict[str, Any] = {}
    for record in records:
        accession = _record_accession(record)
        records_by_accession[accession] = record

    source_snapshot_id = _clean_text(
        manifest.get("corpus_snapshot_id")
        or provenance.get("corpus_snapshot_id")
        or _result_value(snapshot_result, "corpus_snapshot_id")
        or ""
    )
    aligner_version = _mapping_text(manifest, "aligner_version") or _mapping_text(
        provenance,
        "aligner_version",
    )
    source_layers = _dedupe_text(
        manifest.get("source_layers")
        or provenance.get("source_layers")
        or ()
    )

    packet_lanes: list[EvolutionaryPacketLaneEntry] = []
    positive_ordered: list[str] = []
    unresolved_ordered: list[str] = []
    blocked_ordered: list[str] = []

    if snapshot_status in {"blocked", "unavailable"} and not records_by_accession:
        blocker_reason = snapshot_reason or "evolutionary_snapshot_unavailable"
        for accession in normalized_accessions:
            blocked_ordered.append(accession)
            packet_lanes.append(
                EvolutionaryPacketLaneEntry(
                    accession=accession,
                    lane_state="blocked",
                    lane_depth=0,
                    corpus_snapshot_id=source_snapshot_id or None,
                    aligner_version=aligner_version or None,
                    source_layers=source_layers,
                    blocker_reason=blocker_reason,
                    notes=("evolutionary snapshot unavailable",),
                )
            )
        summary = {
            "cohort_accession_count": len(normalized_accessions),
            "lane_count": len(packet_lanes),
            "positive_count": 0,
            "unresolved_count": 0,
            "blocked_count": len(blocked_ordered),
            "materialized_count": 0,
            "snapshot_record_count": 0,
        }
        return EvolutionaryPacketLaneResult(
            cohort_accessions=normalized_accessions,
            packet_lanes=tuple(packet_lanes),
            positive_accessions=(),
            unresolved_accessions=(),
            blocked_accessions=tuple(blocked_ordered),
            snapshot_status=snapshot_status,
            snapshot_reason=snapshot_reason or None,
            snapshot_record_count=0,
            source_snapshot_id=source_snapshot_id or None,
            aligner_version=aligner_version or None,
            source_layers=source_layers,
            summary=summary,
        )

    for accession in normalized_accessions:
        record = records_by_accession.get(accession)
        if record is None:
            unresolved_ordered.append(accession)
            packet_lanes.append(
                EvolutionaryPacketLaneEntry(
                    accession=accession,
                    lane_state="unresolved",
                    lane_depth=0,
                    corpus_snapshot_id=source_snapshot_id or None,
                    aligner_version=aligner_version or None,
                    source_layers=source_layers,
                    notes=("no evolutionary record materialized for this accession",),
                )
            )
            continue

        positive_ordered.append(accession)
        record_metadata = _record_value(record, "metadata", {})
        if not isinstance(record_metadata, Mapping):
            record_metadata = {}
        packet_lanes.append(
            EvolutionaryPacketLaneEntry(
                accession=accession,
                lane_state="positive_hit",
                lane_depth=1,
                corpus_snapshot_id=(
                    _mapping_text(record_metadata, "corpus_snapshot_id")
                    or source_snapshot_id
                    or None
                ),
                aligner_version=(
                    _mapping_text(record_metadata, "aligner_version")
                    or aligner_version
                    or None
                ),
                source_layers=(
                    _dedupe_text(record_metadata.get("source_layers")) or source_layers
                ),
                sequence_version=_clean_text(_record_value(record, "sequence_version")) or None,
                sequence_hash=_clean_text(_record_value(record, "sequence_hash")) or None,
                sequence_length=_record_int(record, "sequence_length"),
                taxon_id=_record_int(record, "taxon_id"),
                alignment_depth=_record_int(record, "alignment_depth"),
                alignment_coverage=_record_float(record, "alignment_coverage"),
                neff=_record_float(record, "neff"),
                gap_fraction=_record_float(record, "gap_fraction"),
                uniref_cluster_ids=_dedupe_text(_record_value(record, "uniref_cluster_ids")),
                orthogroup_ids=_dedupe_text(_record_value(record, "orthogroup_ids")),
                quality_flags=_dedupe_text(_record_value(record, "quality_flags")),
                source_refs=_dedupe_text(_record_value(record, "source_refs")),
                lazy_materialization_refs=_dedupe_text(
                    _record_value(record, "lazy_materialization_refs")
                ),
                notes=("pinned MSA-related context available",),
            )
        )

    summary = {
        "cohort_accession_count": len(normalized_accessions),
        "lane_count": len(packet_lanes),
        "positive_count": len(positive_ordered),
        "unresolved_count": len(unresolved_ordered),
        "blocked_count": len(blocked_ordered),
        "materialized_count": len(positive_ordered),
        "snapshot_record_count": len(records_by_accession),
    }
    return EvolutionaryPacketLaneResult(
        cohort_accessions=normalized_accessions,
        packet_lanes=tuple(packet_lanes),
        positive_accessions=tuple(positive_ordered),
        unresolved_accessions=tuple(unresolved_ordered),
        blocked_accessions=tuple(blocked_ordered),
        snapshot_status=snapshot_status,
        snapshot_reason=snapshot_reason or None,
        snapshot_record_count=len(records_by_accession),
        source_snapshot_id=source_snapshot_id or None,
        aligner_version=aligner_version or None,
        source_layers=source_layers,
        summary=summary,
    )


__all__ = [
    "EvolutionaryPacketLaneEntry",
    "EvolutionaryPacketLaneError",
    "EvolutionaryPacketLaneResult",
    "EvolutionaryPacketLaneState",
    "build_evolutionary_packet_lane",
]
