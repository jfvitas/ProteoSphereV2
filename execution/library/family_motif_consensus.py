from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from core.library.summary_record import ProteinSummaryRecord, SummaryLibrarySchema, SummaryReference

ConsensusState = Literal["consensus", "mixed", "empty"]
ConsensusReferenceKind = Literal["motif", "domain"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


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


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


@dataclass(frozen=True, slots=True)
class FamilyMotifConsensusEntry:
    reference_kind: ConsensusReferenceKind
    namespace: str
    identifier: str
    label: str = ""
    consensus_state: ConsensusState = "mixed"
    support_count: int = 0
    record_count: int = 0
    joined_count: int = 0
    support_ratio: float = 0.0
    observed_in: tuple[str, ...] = ()
    join_statuses: tuple[str, ...] = ()
    source_names: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_kind", _clean_text(self.reference_kind))
        object.__setattr__(self, "namespace", _clean_text(self.namespace))
        object.__setattr__(self, "identifier", _clean_text(self.identifier))
        object.__setattr__(self, "label", _clean_text(self.label))
        object.__setattr__(self, "consensus_state", _clean_text(self.consensus_state))
        object.__setattr__(self, "support_count", int(self.support_count))
        object.__setattr__(self, "record_count", int(self.record_count))
        object.__setattr__(self, "joined_count", int(self.joined_count))
        object.__setattr__(self, "support_ratio", float(self.support_ratio))
        object.__setattr__(self, "observed_in", _clean_text_tuple(self.observed_in))
        object.__setattr__(self, "join_statuses", _clean_text_tuple(self.join_statuses))
        object.__setattr__(self, "source_names", _clean_text_tuple(self.source_names))
        object.__setattr__(self, "evidence_refs", _clean_text_tuple(self.evidence_refs))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if self.reference_kind not in {"motif", "domain"}:
            raise ValueError("reference_kind must be motif or domain")
        if self.consensus_state not in {"consensus", "mixed", "empty"}:
            raise ValueError("consensus_state must be consensus, mixed, or empty")
        if not self.namespace:
            raise ValueError("namespace must not be empty")
        if not self.identifier:
            raise ValueError("identifier must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_kind": self.reference_kind,
            "namespace": self.namespace,
            "identifier": self.identifier,
            "label": self.label,
            "consensus_state": self.consensus_state,
            "support_count": self.support_count,
            "record_count": self.record_count,
            "joined_count": self.joined_count,
            "support_ratio": self.support_ratio,
            "observed_in": list(self.observed_in),
            "join_statuses": list(self.join_statuses),
            "source_names": list(self.source_names),
            "evidence_refs": list(self.evidence_refs),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class FamilyMotifConsensus:
    group_id: str
    record_refs: tuple[str, ...]
    motif_state: ConsensusState
    domain_state: ConsensusState
    overall_state: ConsensusState
    motif_entries: tuple[FamilyMotifConsensusEntry, ...] = ()
    domain_entries: tuple[FamilyMotifConsensusEntry, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "group_id", _clean_text(self.group_id))
        object.__setattr__(self, "record_refs", _clean_text_tuple(self.record_refs))
        object.__setattr__(self, "motif_state", _clean_text(self.motif_state))
        object.__setattr__(self, "domain_state", _clean_text(self.domain_state))
        object.__setattr__(self, "overall_state", _clean_text(self.overall_state))
        object.__setattr__(self, "motif_entries", tuple(self.motif_entries))
        object.__setattr__(self, "domain_entries", tuple(self.domain_entries))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.group_id:
            raise ValueError("group_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "record_refs": list(self.record_refs),
            "motif_state": self.motif_state,
            "domain_state": self.domain_state,
            "overall_state": self.overall_state,
            "motif_entries": [entry.to_dict() for entry in self.motif_entries],
            "domain_entries": [entry.to_dict() for entry in self.domain_entries],
            "notes": list(self.notes),
        }


def _coerce_protein_records(records: object) -> tuple[ProteinSummaryRecord, ...]:
    if isinstance(records, SummaryLibrarySchema):
        return records.protein_records
    if isinstance(records, Mapping):
        if "records" in records or "summary_records" in records:
            return SummaryLibrarySchema.from_dict(records).protein_records
        return (ProteinSummaryRecord.from_dict(records),)
    if isinstance(records, Iterable) and not isinstance(records, (str, bytes)):
        normalized = []
        for item in records:
            if isinstance(item, ProteinSummaryRecord):
                normalized.append(item)
            elif isinstance(item, Mapping):
                normalized.append(ProteinSummaryRecord.from_dict(item))
            else:
                raise TypeError("records must contain ProteinSummaryRecord objects or mappings")
        return tuple(normalized)
    raise TypeError("records must be a summary library schema or iterable of protein records")


def _entry_state(
    *,
    support_count: int,
    record_count: int,
    join_statuses: tuple[str, ...],
) -> ConsensusState:
    if support_count == 0:
        return "empty"
    if support_count == record_count and {
        status.casefold() for status in join_statuses
    } == {"joined"}:
        return "consensus"
    return "mixed"


def _aggregate_entries(
    records: tuple[ProteinSummaryRecord, ...],
    *,
    reference_kind: ConsensusReferenceKind,
) -> tuple[FamilyMotifConsensusEntry, ...]:
    aggregated: dict[tuple[str, str], dict[str, Any]] = {}
    record_count = len(records)

    for record in records:
        references: tuple[SummaryReference, ...]
        if reference_kind == "motif":
            references = tuple(record.context.motif_references)
        else:
            references = tuple(record.context.domain_references)
        for reference in references:
            key = (reference.namespace.casefold(), reference.identifier.casefold())
            bucket = aggregated.setdefault(
                key,
                {
                    "namespace": reference.namespace,
                    "identifier": reference.identifier,
                    "label": reference.label,
                    "observed_in": [],
                    "join_statuses": [],
                    "source_names": [],
                    "evidence_refs": [],
                    "notes": [],
                    "joined_count": 0,
                },
            )
            bucket["observed_in"].append(record.summary_id)
            bucket["join_statuses"].append(reference.join_status)
            if reference.source_name:
                bucket["source_names"].append(reference.source_name)
            bucket["evidence_refs"].extend(reference.evidence_refs)
            bucket["notes"].extend(reference.notes)
            if reference.join_status == "joined":
                bucket["joined_count"] += 1

    entries: list[FamilyMotifConsensusEntry] = []
    for bucket in aggregated.values():
        support_count = len(
            {
                _clean_text(value)
                for value in bucket["observed_in"]
                if _clean_text(value)
            }
        )
        join_statuses = _clean_text_tuple(bucket["join_statuses"])
        notes = list(_clean_text_tuple(bucket["notes"]))
        state = _entry_state(
            support_count=support_count,
            record_count=record_count,
            join_statuses=join_statuses,
        )
        if support_count < record_count:
            notes.append("not_present_across_all_records")
        if set(status.casefold() for status in join_statuses) != {"joined"}:
            notes.append("contains_non_joined_evidence")
        entries.append(
            FamilyMotifConsensusEntry(
                reference_kind=reference_kind,
                namespace=bucket["namespace"],
                identifier=bucket["identifier"],
                label=bucket["label"],
                consensus_state=state,
                support_count=support_count,
                record_count=record_count,
                joined_count=bucket["joined_count"],
                support_ratio=(0.0 if record_count == 0 else support_count / record_count),
                observed_in=tuple(bucket["observed_in"]),
                join_statuses=join_statuses,
                source_names=tuple(bucket["source_names"]),
                evidence_refs=tuple(bucket["evidence_refs"]),
                notes=tuple(notes),
            )
        )

    return tuple(
        sorted(
            entries,
            key=lambda entry: (
                0 if entry.consensus_state == "consensus" else 1,
                -entry.support_count,
                entry.namespace.casefold(),
                entry.identifier.casefold(),
            ),
        )
    )


def _collection_state(entries: tuple[FamilyMotifConsensusEntry, ...]) -> ConsensusState:
    if not entries:
        return "empty"
    if all(entry.consensus_state == "consensus" for entry in entries):
        return "consensus"
    return "mixed"


def build_family_motif_consensus(
    records: object,
    *,
    group_id: str | None = None,
) -> FamilyMotifConsensus:
    protein_records = _coerce_protein_records(records)
    resolved_group_id = _optional_text(group_id) or (
        protein_records[0].protein_ref if protein_records else "family-consensus"
    )
    motif_entries = _aggregate_entries(protein_records, reference_kind="motif")
    domain_entries = _aggregate_entries(protein_records, reference_kind="domain")
    motif_state = _collection_state(motif_entries)
    domain_state = _collection_state(domain_entries)
    overall_state: ConsensusState
    if motif_state == "empty" and domain_state == "empty":
        overall_state = "empty"
    elif motif_state == "consensus" and domain_state in {"consensus", "empty"}:
        overall_state = "consensus"
    elif domain_state == "consensus" and motif_state in {"consensus", "empty"}:
        overall_state = "consensus"
    else:
        overall_state = "mixed"

    notes: list[str] = []
    if motif_state == "empty":
        notes.append("motif_consensus_empty")
    if domain_state == "empty":
        notes.append("domain_consensus_empty")
    if overall_state == "mixed":
        notes.append("mixed_consensus_requires_trace_review")

    return FamilyMotifConsensus(
        group_id=resolved_group_id,
        record_refs=tuple(record.summary_id for record in protein_records),
        motif_state=motif_state,
        domain_state=domain_state,
        overall_state=overall_state,
        motif_entries=motif_entries,
        domain_entries=domain_entries,
        notes=tuple(notes),
    )


__all__ = [
    "ConsensusReferenceKind",
    "ConsensusState",
    "FamilyMotifConsensus",
    "FamilyMotifConsensusEntry",
    "build_family_motif_consensus",
]
