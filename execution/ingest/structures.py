from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from connectors.rcsb.parsers import (
    RCSBStructureBundle,
    parse_structure_bundle,
)
from core.canonical.registry import (
    CanonicalEntityRegistry,
    UnresolvedCanonicalReference,
)
from core.provenance.record import ProvenanceRecord, ProvenanceSource
from execution.acquire.alphafold_snapshot import AlphaFoldSnapshotRecord

StructureIngestStatus = Literal["resolved", "partial", "conflict", "unresolved"]
StructureAlignmentStatus = Literal["resolved", "ambiguous", "unresolved", "provisional"]
StructureConflictKind = Literal[
    "sequence_conflict",
    "identity_conflict",
    "mapping_conflict",
    "assembly_conflict",
]
StructureGraphRelation = Literal["protein_to_chain", "chain_to_complex"]

_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _normalize_sequence(value: Any) -> str:
    sequence = "".join(str(value or "").split()).upper()
    if not sequence:
        raise ValueError("sequence must not be empty")
    invalid = sorted(set(sequence) - _AMINO_ACIDS)
    if invalid:
        raise ValueError("sequence contains invalid residue codes: " + ", ".join(invalid))
    return sequence


def _normalize_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise TypeError("value must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("value must be an integer") from exc


def _normalize_text_tuple(values: Iterable[Any] | None) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _normalize_quality_flags(values: Iterable[Any] | None) -> tuple[str, ...]:
    return _normalize_text_tuple(values)


def _sequence_hash(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("utf-8")).hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _clean_provenance_refs(values: Iterable[Any] | None) -> tuple[str, ...]:
    refs: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        ref = _clean_text(value)
        if not ref or ref in seen:
            continue
        seen.add(ref)
        refs.append(ref)
    return tuple(refs)


def _coerce_provenance_records(
    provenance: Iterable[ProvenanceRecord | Mapping[str, Any] | str] | None,
) -> tuple[ProvenanceRecord, tuple[str, ...]]:
    records: list[ProvenanceRecord] = []
    refs: list[str] = []
    for item in provenance or ():
        if isinstance(item, ProvenanceRecord):
            records.append(item)
            refs.append(item.provenance_id)
        elif isinstance(item, Mapping):
            record = ProvenanceRecord.from_dict(item)
            records.append(record)
            refs.append(record.provenance_id)
        else:
            ref = _clean_text(item)
            if ref:
                refs.append(ref)
    return tuple(records), tuple(dict.fromkeys(refs))


def _source_name_for(item: Any) -> str:
    if isinstance(item, RCSBStructureBundle):
        return "RCSB PDB"
    if isinstance(item, AlphaFoldSnapshotRecord):
        return "AlphaFold DB"
    raise TypeError(f"unsupported structure record type: {type(item)!r}")


def _source_identifier_for(item: Any) -> str:
    if isinstance(item, RCSBStructureBundle):
        return item.entry.pdb_id
    if isinstance(item, AlphaFoldSnapshotRecord):
        return _clean_text(item.qualifier or item.model_entity_id)
    raise TypeError(f"unsupported structure record type: {type(item)!r}")


def _release_version_for(item: Any) -> str | None:
    if isinstance(item, RCSBStructureBundle):
        return _optional_text(item.entry.release_date)
    if isinstance(item, AlphaFoldSnapshotRecord):
        return _optional_text(item.provenance.source_release.release_version)
    return None


def _acquired_at_for(item: Any) -> str | None:
    if isinstance(item, AlphaFoldSnapshotRecord):
        return _optional_text(item.provenance.fetched_at)
    return None


def _source_summary_for(item: Any) -> dict[str, Any]:
    if isinstance(item, RCSBStructureBundle):
        return {
            "entry_title": item.entry.title,
            "experimental_methods": list(item.entry.experimental_methods),
            "assembly_count": len(item.assemblies),
            "entity_count": len(item.entities),
        }
    if isinstance(item, AlphaFoldSnapshotRecord):
        summary = {
            "structure_kind": item.structure_kind,
            "model_entity_id": item.model_entity_id,
            "provider_id": item.provider_id,
            "tool_used": item.tool_used,
            "global_metric_value": item.confidence.global_metric_value,
        }
        if item.structure_kind == "complex":
            summary["assembly_type"] = item.assembly_type
            summary["oligomeric_state"] = item.oligomeric_state
        return summary
    raise TypeError(f"unsupported structure record type: {type(item)!r}")


def _derive_source_provenance(
    item: Any,
    *,
    parent_ids: tuple[str, ...],
) -> ProvenanceRecord:
    source_name = _source_name_for(item)
    source_identifier = _source_identifier_for(item)
    release_version = _release_version_for(item)
    summary = _source_summary_for(item)
    checksum = hashlib.sha256(
        json.dumps(summary, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    provenance_id = f"prov:structure:{source_name.casefold().replace(' ', '_')}:{source_identifier}"
    return ProvenanceRecord(
        provenance_id=provenance_id,
        source=ProvenanceSource(
            source_name=source_name,
            acquisition_mode="derived",
            original_identifier=source_identifier,
            release_version=release_version,
        ),
        transformation_step="structure_ingest",
        acquired_at=_acquired_at_for(item),
        parser_version=None,
        transformation_history=(),
        parent_ids=parent_ids,
        confidence=None,
        checksum=checksum,
        raw_payload_pointer=provenance_id,
        metadata=summary,
    )


@dataclass(frozen=True, slots=True)
class StructureAlignmentSummary:
    status: StructureAlignmentStatus
    canonical_protein_internal_id: str | None = None
    observed_sequence_hash: str | None = None
    identity: float | None = None
    candidates: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", _normalize_text_tuple(self.candidates))
        object.__setattr__(self, "notes", _normalize_text_tuple(self.notes))
        object.__setattr__(
            self,
            "canonical_protein_internal_id",
            _optional_text(self.canonical_protein_internal_id),
        )
        object.__setattr__(
            self, "observed_sequence_hash", _optional_text(self.observed_sequence_hash)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "canonical_protein_internal_id": self.canonical_protein_internal_id,
            "observed_sequence_hash": self.observed_sequence_hash,
            "identity": self.identity,
            "candidates": list(self.candidates),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class StructureProteinRecord:
    protein_id_internal: str
    primary_external_id_type: str
    primary_external_id: str
    gene_name: str = ""
    protein_name: str = ""
    organism_name: str = ""
    taxonomy_id: int | None = None
    canonical_sequence: str = ""
    sequence_length: int | None = None
    isoform_id: str | None = None
    sequence_hash: str | None = None
    provenance_refs: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    created_at: str | None = None
    updated_at: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "protein_id_internal", _clean_text(self.protein_id_internal))
        object.__setattr__(
            self,
            "primary_external_id_type",
            _clean_text(self.primary_external_id_type),
        )
        object.__setattr__(self, "primary_external_id", _clean_text(self.primary_external_id))
        sequence = _normalize_sequence(self.canonical_sequence)
        object.__setattr__(self, "canonical_sequence", sequence)
        object.__setattr__(self, "gene_name", _clean_text(self.gene_name))
        object.__setattr__(self, "protein_name", _clean_text(self.protein_name))
        object.__setattr__(self, "organism_name", _clean_text(self.organism_name))
        object.__setattr__(self, "taxonomy_id", _normalize_int(self.taxonomy_id))
        object.__setattr__(self, "sequence_length", _normalize_int(self.sequence_length))
        object.__setattr__(self, "isoform_id", _optional_text(self.isoform_id))
        object.__setattr__(self, "sequence_hash", _optional_text(self.sequence_hash))
        object.__setattr__(self, "provenance_refs", _clean_provenance_refs(self.provenance_refs))
        object.__setattr__(self, "quality_flags", _normalize_quality_flags(self.quality_flags))
        object.__setattr__(self, "created_at", _optional_text(self.created_at))
        object.__setattr__(self, "updated_at", _optional_text(self.updated_at))
        if not self.protein_id_internal:
            raise ValueError("protein_id_internal must not be empty")
        if not self.primary_external_id_type:
            raise ValueError("primary_external_id_type must not be empty")
        if not self.primary_external_id:
            raise ValueError("primary_external_id must not be empty")
        if self.sequence_length is None:
            object.__setattr__(self, "sequence_length", len(sequence))
        if self.sequence_hash is None:
            object.__setattr__(self, "sequence_hash", _sequence_hash(sequence))
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "protein_id_internal": self.protein_id_internal,
            "primary_external_id_type": self.primary_external_id_type,
            "primary_external_id": self.primary_external_id,
            "gene_name": self.gene_name,
            "protein_name": self.protein_name,
            "organism_name": self.organism_name,
            "taxonomy_id": self.taxonomy_id,
            "canonical_sequence": self.canonical_sequence,
            "sequence_length": self.sequence_length,
            "isoform_id": self.isoform_id,
            "sequence_hash": self.sequence_hash,
            "provenance_refs": list(self.provenance_refs),
            "quality_flags": list(self.quality_flags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class UnresolvedStructureReference:
    reference_type: Literal["protein", "chain", "complex", "ligand", "nucleic_acid"]
    reference_id: str
    reason: str
    candidates: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_type", _clean_text(self.reference_type))
        object.__setattr__(self, "reference_id", _clean_text(self.reference_id))
        object.__setattr__(self, "reason", _clean_text(self.reason) or "missing")
        object.__setattr__(self, "candidates", _normalize_text_tuple(self.candidates))
        object.__setattr__(self, "provenance_refs", _clean_provenance_refs(self.provenance_refs))
        if not self.reference_type:
            raise ValueError("reference_type must not be empty")
        if not self.reference_id:
            raise ValueError("reference_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "reason": self.reason,
            "candidates": list(self.candidates),
            "provenance_refs": list(self.provenance_refs),
        }


@dataclass(frozen=True, slots=True)
class StructureChainRecord:
    chain_id_internal: str
    structure_source: str
    structure_id: str
    model_id: str | None = None
    assembly_id: str | None = None
    entity_id: str | None = None
    chain_label: str = ""
    auth_chain_label: str | None = None
    mapped_protein_internal_id: str | None = None
    extracted_sequence: str = ""
    sequence_alignment_to_canonical: StructureAlignmentSummary | None = None
    mutation_summary: tuple[str, ...] = ()
    missing_residue_ranges: tuple[str, ...] = ()
    altloc_summary: tuple[str, ...] = ()
    confidence_summary: dict[str, Any] = field(default_factory=dict)
    provenance_refs: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    unresolved_protein_reference: UnresolvedStructureReference | None = None
    created_at: str | None = None
    updated_at: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "chain_id_internal", _clean_text(self.chain_id_internal))
        object.__setattr__(self, "structure_source", _clean_text(self.structure_source))
        object.__setattr__(self, "structure_id", _clean_text(self.structure_id))
        object.__setattr__(self, "model_id", _optional_text(self.model_id))
        object.__setattr__(self, "assembly_id", _optional_text(self.assembly_id))
        object.__setattr__(self, "entity_id", _optional_text(self.entity_id))
        object.__setattr__(self, "chain_label", _clean_text(self.chain_label))
        object.__setattr__(self, "auth_chain_label", _optional_text(self.auth_chain_label))
        object.__setattr__(
            self, "mapped_protein_internal_id", _optional_text(self.mapped_protein_internal_id)
        )
        object.__setattr__(
            self, "extracted_sequence", _optional_text(self.extracted_sequence) or ""
        )
        object.__setattr__(self, "mutation_summary", _normalize_text_tuple(self.mutation_summary))
        object.__setattr__(
            self, "missing_residue_ranges", _normalize_text_tuple(self.missing_residue_ranges)
        )
        object.__setattr__(self, "altloc_summary", _normalize_text_tuple(self.altloc_summary))
        object.__setattr__(self, "provenance_refs", _clean_provenance_refs(self.provenance_refs))
        object.__setattr__(self, "quality_flags", _normalize_quality_flags(self.quality_flags))
        object.__setattr__(self, "created_at", _optional_text(self.created_at))
        object.__setattr__(self, "updated_at", _optional_text(self.updated_at))
        if not self.chain_id_internal:
            raise ValueError("chain_id_internal must not be empty")
        if not self.structure_source:
            raise ValueError("structure_source must not be empty")
        if not self.structure_id:
            raise ValueError("structure_id must not be empty")
        if not self.chain_label:
            raise ValueError("chain_label must not be empty")
        if self.sequence_alignment_to_canonical is not None and not isinstance(
            self.sequence_alignment_to_canonical,
            StructureAlignmentSummary,
        ):
            raise TypeError("sequence_alignment_to_canonical must be a StructureAlignmentSummary")
        if self.unresolved_protein_reference is not None and not isinstance(
            self.unresolved_protein_reference,
            UnresolvedStructureReference,
        ):
            raise TypeError("unresolved_protein_reference must be an UnresolvedStructureReference")
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id_internal": self.chain_id_internal,
            "structure_source": self.structure_source,
            "structure_id": self.structure_id,
            "model_id": self.model_id,
            "assembly_id": self.assembly_id,
            "entity_id": self.entity_id,
            "chain_label": self.chain_label,
            "auth_chain_label": self.auth_chain_label,
            "mapped_protein_internal_id": self.mapped_protein_internal_id,
            "extracted_sequence": self.extracted_sequence,
            "sequence_alignment_to_canonical": (
                None
                if self.sequence_alignment_to_canonical is None
                else self.sequence_alignment_to_canonical.to_dict()
            ),
            "mutation_summary": list(self.mutation_summary),
            "missing_residue_ranges": list(self.missing_residue_ranges),
            "altloc_summary": list(self.altloc_summary),
            "confidence_summary": _json_ready(self.confidence_summary),
            "provenance_refs": list(self.provenance_refs),
            "quality_flags": list(self.quality_flags),
            "unresolved_protein_reference": (
                None
                if self.unresolved_protein_reference is None
                else self.unresolved_protein_reference.to_dict()
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class StructureComplexRecord:
    complex_id_internal: str
    complex_type: Literal["protein", "protein_ligand", "protein_protein", "protein_na", "mixed"]
    structure_source: str
    structure_id: str
    assembly_id: str | None = None
    member_chain_ids: tuple[str, ...] = ()
    member_ligand_ids: tuple[str, ...] = ()
    member_na_ids: tuple[str, ...] = ()
    stoichiometry: dict[str, int] = field(default_factory=dict)
    biologically_relevant_flag: bool | None = None
    relevance_confidence: float | None = None
    extraction_notes: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    created_at: str | None = None
    updated_at: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "complex_id_internal", _clean_text(self.complex_id_internal))
        object.__setattr__(self, "structure_source", _clean_text(self.structure_source))
        object.__setattr__(self, "structure_id", _clean_text(self.structure_id))
        object.__setattr__(self, "assembly_id", _optional_text(self.assembly_id))
        object.__setattr__(self, "member_chain_ids", _normalize_text_tuple(self.member_chain_ids))
        object.__setattr__(self, "member_ligand_ids", _normalize_text_tuple(self.member_ligand_ids))
        object.__setattr__(self, "member_na_ids", _normalize_text_tuple(self.member_na_ids))
        object.__setattr__(
            self,
            "stoichiometry",
            {str(key): int(value) for key, value in self.stoichiometry.items()},
        )
        object.__setattr__(self, "extraction_notes", _normalize_text_tuple(self.extraction_notes))
        object.__setattr__(self, "provenance_refs", _clean_provenance_refs(self.provenance_refs))
        object.__setattr__(self, "quality_flags", _normalize_quality_flags(self.quality_flags))
        object.__setattr__(self, "created_at", _optional_text(self.created_at))
        object.__setattr__(self, "updated_at", _optional_text(self.updated_at))
        if not self.complex_id_internal:
            raise ValueError("complex_id_internal must not be empty")
        if not self.structure_source:
            raise ValueError("structure_source must not be empty")
        if not self.structure_id:
            raise ValueError("structure_id must not be empty")
        if not self.complex_type:
            raise ValueError("complex_type must not be empty")
        if self.relevance_confidence is not None and not (0.0 <= self.relevance_confidence <= 1.0):
            raise ValueError("relevance_confidence must be between 0.0 and 1.0")
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "complex_id_internal": self.complex_id_internal,
            "complex_type": self.complex_type,
            "structure_source": self.structure_source,
            "structure_id": self.structure_id,
            "assembly_id": self.assembly_id,
            "member_chain_ids": list(self.member_chain_ids),
            "member_ligand_ids": list(self.member_ligand_ids),
            "member_na_ids": list(self.member_na_ids),
            "stoichiometry": dict(self.stoichiometry),
            "biologically_relevant_flag": self.biologically_relevant_flag,
            "relevance_confidence": self.relevance_confidence,
            "extraction_notes": list(self.extraction_notes),
            "provenance_refs": list(self.provenance_refs),
            "quality_flags": list(self.quality_flags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class StructureGraphEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation: StructureGraphRelation
    provenance_refs: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", _clean_text(self.edge_id))
        object.__setattr__(self, "source_id", _clean_text(self.source_id))
        object.__setattr__(self, "target_id", _clean_text(self.target_id))
        object.__setattr__(self, "provenance_refs", _clean_provenance_refs(self.provenance_refs))
        object.__setattr__(self, "quality_flags", _normalize_quality_flags(self.quality_flags))
        if not self.edge_id:
            raise ValueError("edge_id must not be empty")
        if not self.source_id:
            raise ValueError("source_id must not be empty")
        if not self.target_id:
            raise ValueError("target_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "provenance_refs": list(self.provenance_refs),
            "quality_flags": list(self.quality_flags),
        }


@dataclass(frozen=True, slots=True)
class StructureIngestConflict:
    conflict_id: str
    kind: StructureConflictKind
    subject_id: str
    message: str
    observed_values: dict[str, tuple[str, ...]]
    provenance_refs: tuple[str, ...] = ()
    related_record_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "conflict_id", _clean_text(self.conflict_id))
        object.__setattr__(self, "kind", _clean_text(self.kind))
        object.__setattr__(self, "subject_id", _clean_text(self.subject_id))
        object.__setattr__(self, "message", _clean_text(self.message))
        object.__setattr__(
            self,
            "observed_values",
            {
                _clean_text(key): _normalize_text_tuple(values)
                for key, values in self.observed_values.items()
            },
        )
        object.__setattr__(self, "provenance_refs", _clean_provenance_refs(self.provenance_refs))
        object.__setattr__(
            self, "related_record_ids", _normalize_text_tuple(self.related_record_ids)
        )
        if not self.conflict_id:
            raise ValueError("conflict_id must not be empty")
        if not self.kind:
            raise ValueError("kind must not be empty")
        if not self.subject_id:
            raise ValueError("subject_id must not be empty")
        if not self.message:
            raise ValueError("message must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "kind": self.kind,
            "subject_id": self.subject_id,
            "message": self.message,
            "observed_values": {
                key: list(values) for key, values in sorted(self.observed_values.items())
            },
            "provenance_refs": list(self.provenance_refs),
            "related_record_ids": list(self.related_record_ids),
        }


@dataclass(frozen=True, slots=True)
class StructureIngestResult:
    status: StructureIngestStatus
    proteins: tuple[StructureProteinRecord, ...]
    chains: tuple[StructureChainRecord, ...]
    complexes: tuple[StructureComplexRecord, ...]
    provenance_records: tuple[ProvenanceRecord, ...]
    unresolved_references: tuple[UnresolvedStructureReference, ...]
    conflicts: tuple[StructureIngestConflict, ...]
    graph_edges: tuple[StructureGraphEdge, ...]

    @property
    def canonical_records(self) -> tuple[Any, ...]:
        return self.proteins + self.chains + self.complexes

    @property
    def unresolved_cases(self) -> tuple[UnresolvedStructureReference, ...]:
        return self.unresolved_references

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "proteins": [record.to_dict() for record in self.proteins],
            "chains": [record.to_dict() for record in self.chains],
            "complexes": [record.to_dict() for record in self.complexes],
            "canonical_records": [record.to_dict() for record in self.canonical_records],
            "provenance_records": [record.to_dict() for record in self.provenance_records],
            "unresolved_references": [record.to_dict() for record in self.unresolved_references],
            "conflicts": [record.to_dict() for record in self.conflicts],
            "graph_edges": [edge.to_dict() for edge in self.graph_edges],
        }


def ingest_structure_bundle(
    bundle: RCSBStructureBundle | Mapping[str, Any] | AlphaFoldSnapshotRecord,
    *,
    provenance: Iterable[ProvenanceRecord | Mapping[str, Any] | str] | None = None,
    registry: CanonicalEntityRegistry | None = None,
) -> StructureIngestResult:
    return ingest_structure_records(bundle, provenance=provenance, registry=registry)


def ingest_structure_records(
    records: object,
    *,
    provenance: Iterable[ProvenanceRecord | Mapping[str, Any] | str] | None = None,
    registry: CanonicalEntityRegistry | None = None,
) -> StructureIngestResult:
    inputs = _coerce_structure_inputs(records)
    explicit_provenance_records, explicit_provenance_refs = _coerce_provenance_records(provenance)

    proteins_by_key: dict[tuple[str, str, str], StructureProteinRecord] = {}
    proteins_by_accession: dict[str, list[str]] = {}
    chains: list[StructureChainRecord] = []
    complexes: list[StructureComplexRecord] = []
    unresolved: list[UnresolvedStructureReference] = []
    conflicts: list[StructureIngestConflict] = []
    graph_edges: list[StructureGraphEdge] = []
    provenance_records: list[ProvenanceRecord] = list(explicit_provenance_records)

    for item in inputs:
        if isinstance(item, RCSBStructureBundle):
            source_provenance = _derive_source_provenance(item, parent_ids=explicit_provenance_refs)
            provenance_records.append(source_provenance)
            _ingest_rcsb_bundle(
                item,
                source_provenance=source_provenance,
                registry=registry,
                proteins_by_key=proteins_by_key,
                proteins_by_accession=proteins_by_accession,
                chains=chains,
                complexes=complexes,
                unresolved=unresolved,
                conflicts=conflicts,
                graph_edges=graph_edges,
            )
            continue
        if isinstance(item, AlphaFoldSnapshotRecord):
            source_provenance = _derive_source_provenance(item, parent_ids=explicit_provenance_refs)
            provenance_records.append(source_provenance)
            _ingest_alphafold_record(
                item,
                source_provenance=source_provenance,
                registry=registry,
                proteins_by_key=proteins_by_key,
                proteins_by_accession=proteins_by_accession,
                chains=chains,
                complexes=complexes,
                unresolved=unresolved,
                conflicts=conflicts,
                graph_edges=graph_edges,
            )
            continue
        raise TypeError(f"unsupported structure record type: {type(item)!r}")

    proteins = tuple(proteins_by_key.values())
    status = _status_for_result(proteins, chains, complexes, unresolved, conflicts)
    provenance_unique: list[ProvenanceRecord] = []
    seen_provenance_ids: set[str] = set()
    for record in provenance_records:
        if record.provenance_id in seen_provenance_ids:
            continue
        seen_provenance_ids.add(record.provenance_id)
        provenance_unique.append(record)
    return StructureIngestResult(
        status=status,
        proteins=proteins,
        chains=tuple(chains),
        complexes=tuple(complexes),
        provenance_records=tuple(provenance_unique),
        unresolved_references=tuple(unresolved),
        conflicts=tuple(conflicts),
        graph_edges=tuple(graph_edges),
    )


def _coerce_structure_inputs(records: object) -> tuple[Any, ...]:
    if isinstance(records, (RCSBStructureBundle, AlphaFoldSnapshotRecord)):
        return (records,)
    if isinstance(records, Mapping):
        return (_coerce_structure_mapping(records),)
    if isinstance(records, Iterable) and not isinstance(records, (str, bytes)):
        normalized: list[Any] = []
        for item in records:
            if isinstance(item, Mapping):
                normalized.append(_coerce_structure_mapping(item))
            else:
                normalized.append(item)
        return tuple(normalized)
    raise TypeError("records must be a structure bundle, structure record, or iterable")


def _coerce_structure_mapping(payload: Mapping[str, Any]) -> Any:
    if "entry" in payload and "entities" in payload and "assemblies" in payload:
        return parse_structure_bundle(
            dict(payload["entry"]),
            [dict(entity) for entity in payload["entities"]],
            [dict(assembly) for assembly in payload["assemblies"]],
        )
    raise TypeError("unsupported structure mapping payload")


def _resolve_registry_candidates(
    registry: CanonicalEntityRegistry | None,
    accession: str,
) -> tuple[str, ...]:
    if registry is None:
        return ()
    resolved = registry.resolve(accession, entity_type="protein")
    if isinstance(resolved, UnresolvedCanonicalReference):
        if resolved.reason == "ambiguous":
            return resolved.candidates
        return ()
    return (resolved.canonical_id,)


def _make_protein_record(
    *,
    source_provenance: ProvenanceRecord,
    protein_id_internal: str,
    primary_external_id_type: str,
    primary_external_id: str,
    sequence: str,
    protein_name: str = "",
    gene_name: str = "",
    organism_name: str = "",
    taxonomy_id: int | None = None,
    quality_flags: Iterable[Any] | None = None,
) -> StructureProteinRecord:
    sequence = _normalize_sequence(sequence)
    return StructureProteinRecord(
        protein_id_internal=protein_id_internal,
        primary_external_id_type=primary_external_id_type,
        primary_external_id=primary_external_id,
        gene_name=gene_name,
        protein_name=protein_name,
        organism_name=organism_name,
        taxonomy_id=taxonomy_id,
        canonical_sequence=sequence,
        sequence_length=len(sequence),
        sequence_hash=_sequence_hash(sequence),
        provenance_refs=(source_provenance.provenance_id,),
        quality_flags=quality_flags or (),
        created_at=source_provenance.acquired_at,
        updated_at=source_provenance.acquired_at,
    )


def _upsert_protein(
    *,
    proteins_by_key: dict[tuple[str, str, str], StructureProteinRecord],
    proteins_by_accession: dict[str, list[str]],
    source_provenance: ProvenanceRecord,
    protein_id_internal: str,
    primary_external_id_type: str,
    primary_external_id: str,
    sequence: str,
    protein_name: str = "",
    gene_name: str = "",
    organism_name: str = "",
    taxonomy_id: int | None = None,
    quality_flags: Iterable[Any] | None = None,
) -> StructureProteinRecord:
    sequence = _normalize_sequence(sequence)
    sequence_hash = _sequence_hash(sequence)
    key = (primary_external_id_type, primary_external_id, sequence_hash)
    existing = proteins_by_key.get(key)
    if existing is not None:
        merged_refs = tuple(
            dict.fromkeys((*existing.provenance_refs, source_provenance.provenance_id))
        )
        merged_flags = tuple(
            dict.fromkeys((*existing.quality_flags, *(_normalize_quality_flags(quality_flags))))
        )
        updated = replace(
            existing,
            provenance_refs=merged_refs,
            quality_flags=merged_flags,
        )
        proteins_by_key[key] = updated
        return updated

    record = _make_protein_record(
        source_provenance=source_provenance,
        protein_id_internal=protein_id_internal,
        primary_external_id_type=primary_external_id_type,
        primary_external_id=primary_external_id,
        sequence=sequence,
        protein_name=protein_name,
        gene_name=gene_name,
        organism_name=organism_name,
        taxonomy_id=taxonomy_id,
        quality_flags=quality_flags,
    )
    proteins_by_key[key] = record
    proteins_by_accession.setdefault(primary_external_id, []).append(record.protein_id_internal)
    return record


def _ingest_rcsb_bundle(
    bundle: RCSBStructureBundle,
    *,
    source_provenance: ProvenanceRecord,
    registry: CanonicalEntityRegistry | None,
    proteins_by_key: dict[tuple[str, str, str], StructureProteinRecord],
    proteins_by_accession: dict[str, list[str]],
    chains: list[StructureChainRecord],
    complexes: list[StructureComplexRecord],
    unresolved: list[UnresolvedStructureReference],
    conflicts: list[StructureIngestConflict],
    graph_edges: list[StructureGraphEdge],
) -> None:
    entity_to_chain_ids: dict[str, list[str]] = {}
    entity_to_protein_ids: dict[str, list[str]] = {}

    for entity in bundle.entities:
        entity_key = f"{bundle.entry.pdb_id}:{entity.entity_id}"
        accession_candidates = tuple(dict.fromkeys(_normalize_text_tuple(entity.uniprot_ids)))
        sequence = _optional_text(entity.sequence)
        organism_name = entity.organism_names[0] if entity.organism_names else ""
        taxonomy_id = _normalize_int(entity.taxonomy_ids[0]) if entity.taxonomy_ids else None
        protein_name = entity.description
        if sequence:
            if accession_candidates:
                candidate_ids: list[str] = []
                for accession in accession_candidates:
                    registry_candidates = _resolve_registry_candidates(registry, accession)
                    if registry_candidates:
                        candidate_ids.extend(registry_candidates)
                    else:
                        record = _upsert_protein(
                            proteins_by_key=proteins_by_key,
                            proteins_by_accession=proteins_by_accession,
                            source_provenance=source_provenance,
                            protein_id_internal=f"protein:{accession}",
                            primary_external_id_type="UniProt accession",
                            primary_external_id=accession,
                            sequence=sequence,
                            protein_name=protein_name,
                            organism_name=organism_name,
                            taxonomy_id=taxonomy_id,
                            quality_flags=("uniprot_mapped",),
                        )
                        candidate_ids.append(record.protein_id_internal)

                if len(accession_candidates) > 1:
                    conflicts.append(
                        StructureIngestConflict(
                            conflict_id=f"conflict:protein:{entity_key}",
                            kind="identity_conflict",
                            subject_id=entity_key,
                            message=(
                                "entity exposes multiple UniProt accessions and the chain map "
                                "is ambiguous"
                            ),
                            observed_values={"accessions": accession_candidates},
                            provenance_refs=(source_provenance.provenance_id,),
                            related_record_ids=tuple(candidate_ids),
                        )
                    )
                    unresolved.append(
                        UnresolvedStructureReference(
                            reference_type="protein",
                            reference_id=entity_key,
                            reason="ambiguous_accession_mapping",
                            candidates=tuple(candidate_ids),
                            provenance_refs=(source_provenance.provenance_id,),
                        )
                    )
                entity_to_protein_ids[entity_key] = candidate_ids
            else:
                provisional_id = f"protein:structure:{bundle.entry.pdb_id}:{entity.entity_id}"
                record = _upsert_protein(
                    proteins_by_key=proteins_by_key,
                    proteins_by_accession=proteins_by_accession,
                    source_provenance=source_provenance,
                    protein_id_internal=provisional_id,
                    primary_external_id_type="structure entity",
                    primary_external_id=entity_key,
                    sequence=sequence,
                    protein_name=protein_name,
                    organism_name=organism_name,
                    taxonomy_id=taxonomy_id,
                    quality_flags=("provisional_identity", "no_uniprot_accession"),
                )
                entity_to_protein_ids[entity_key] = [record.protein_id_internal]
        else:
            unresolved.append(
                UnresolvedStructureReference(
                    reference_type="protein",
                    reference_id=entity_key,
                    reason="missing_sequence",
                    candidates=accession_candidates,
                    provenance_refs=(source_provenance.provenance_id,),
                )
            )
            entity_to_protein_ids[entity_key] = []

        for chain_label in entity.chain_ids:
            chain_id_internal = f"chain:rcsb:{bundle.entry.pdb_id}:{entity.entity_id}:{chain_label}"
            candidate_ids = tuple(entity_to_protein_ids.get(entity_key, ()))
            if len(candidate_ids) == 1:
                alignment = StructureAlignmentSummary(
                    status="resolved",
                    canonical_protein_internal_id=candidate_ids[0],
                    observed_sequence_hash=_sequence_hash(_normalize_sequence(sequence))
                    if sequence
                    else None,
                    identity=1.0 if sequence else None,
                    notes=("exact sequence match",),
                )
                mapped_protein_internal_id = candidate_ids[0]
                unresolved_ref = None
                quality_flags = ("protein_mapping_resolved",)
            elif len(candidate_ids) > 1:
                alignment = StructureAlignmentSummary(
                    status="ambiguous",
                    observed_sequence_hash=_sequence_hash(_normalize_sequence(sequence))
                    if sequence
                    else None,
                    candidates=candidate_ids,
                    notes=("multiple candidate proteins preserved",),
                )
                mapped_protein_internal_id = None
                unresolved_ref = UnresolvedStructureReference(
                    reference_type="chain",
                    reference_id=chain_id_internal,
                    reason="ambiguous_protein_mapping",
                    candidates=candidate_ids,
                    provenance_refs=(source_provenance.provenance_id,),
                )
                unresolved.append(unresolved_ref)
                quality_flags = ("protein_mapping_ambiguous",)
            else:
                alignment = StructureAlignmentSummary(
                    status="unresolved",
                    observed_sequence_hash=_sequence_hash(_normalize_sequence(sequence))
                    if sequence
                    else None,
                    notes=("no canonical protein candidate was available",),
                )
                mapped_protein_internal_id = None
                unresolved_ref = UnresolvedStructureReference(
                    reference_type="chain",
                    reference_id=chain_id_internal,
                    reason="missing_primary_identifier",
                    candidates=accession_candidates,
                    provenance_refs=(source_provenance.provenance_id,),
                )
                unresolved.append(unresolved_ref)
                quality_flags = ("protein_mapping_unresolved",)

            chain = StructureChainRecord(
                chain_id_internal=chain_id_internal,
                structure_source="RCSB PDB",
                structure_id=bundle.entry.pdb_id,
                assembly_id=None,
                entity_id=entity.entity_id,
                chain_label=chain_label,
                auth_chain_label=chain_label,
                mapped_protein_internal_id=mapped_protein_internal_id,
                extracted_sequence=sequence or "",
                sequence_alignment_to_canonical=alignment,
                mutation_summary=(),
                missing_residue_ranges=(),
                altloc_summary=(),
                confidence_summary={
                    "source": "RCSB PDB",
                    "entity_id": entity.entity_id,
                    "accessions": list(accession_candidates),
                },
                provenance_refs=(source_provenance.provenance_id,),
                quality_flags=quality_flags,
                unresolved_protein_reference=unresolved_ref,
                created_at=source_provenance.acquired_at,
                updated_at=source_provenance.acquired_at,
            )
            chains.append(chain)
            entity_to_chain_ids.setdefault(entity_key, []).append(chain.chain_id_internal)
            if mapped_protein_internal_id is not None:
                graph_edges.append(
                    StructureGraphEdge(
                        edge_id=f"edge:{mapped_protein_internal_id}->{chain.chain_id_internal}",
                        source_id=mapped_protein_internal_id,
                        target_id=chain.chain_id_internal,
                        relation="protein_to_chain",
                        provenance_refs=(source_provenance.provenance_id,),
                    )
                )

    for assembly in bundle.assemblies:
        member_chain_ids = tuple(
            chain_id
            for entity_key, chain_ids in entity_to_chain_ids.items()
            for chain_id in chain_ids
            if chain_id.split(":")[-1] in assembly.chain_ids
        )
        if not member_chain_ids:
            unresolved.append(
                UnresolvedStructureReference(
                    reference_type="complex",
                    reference_id=f"{bundle.entry.pdb_id}:{assembly.assembly_id}",
                    reason="missing_chain_members",
                    candidates=assembly.chain_ids,
                    provenance_refs=(source_provenance.provenance_id,),
                )
            )
            continue
        complex_type = "protein" if len(member_chain_ids) == 1 else "protein_protein"
        complex_record = StructureComplexRecord(
            complex_id_internal=f"complex:rcsb:{bundle.entry.pdb_id}:assembly:{assembly.assembly_id}",
            complex_type=complex_type,
            structure_source="RCSB PDB",
            structure_id=bundle.entry.pdb_id,
            assembly_id=assembly.assembly_id,
            member_chain_ids=member_chain_ids,
            stoichiometry={chain_id: 1 for chain_id in member_chain_ids},
            biologically_relevant_flag=None,
            relevance_confidence=None,
            extraction_notes=(
                assembly.method
                or assembly.oligomeric_state
                or "assembly preserved without destructive selection",
            ),
            provenance_refs=(source_provenance.provenance_id,),
            quality_flags=("assembly_preserved",),
            created_at=source_provenance.acquired_at,
            updated_at=source_provenance.acquired_at,
        )
        complexes.append(complex_record)
        for chain_id in member_chain_ids:
            graph_edges.append(
                StructureGraphEdge(
                    edge_id=f"edge:{chain_id}->{complex_record.complex_id_internal}",
                    source_id=chain_id,
                    target_id=complex_record.complex_id_internal,
                    relation="chain_to_complex",
                    provenance_refs=(source_provenance.provenance_id,),
                )
            )

    _record_sequence_conflicts(
        proteins_by_key=proteins_by_key,
        conflicts=conflicts,
        source_provenance=source_provenance,
    )


def _ingest_alphafold_record(
    record: AlphaFoldSnapshotRecord,
    *,
    source_provenance: ProvenanceRecord,
    registry: CanonicalEntityRegistry | None,
    proteins_by_key: dict[tuple[str, str, str], StructureProteinRecord],
    proteins_by_accession: dict[str, list[str]],
    chains: list[StructureChainRecord],
    complexes: list[StructureComplexRecord],
    unresolved: list[UnresolvedStructureReference],
    conflicts: list[StructureIngestConflict],
    graph_edges: list[StructureGraphEdge],
) -> None:
    source_id = _clean_text(record.qualifier or record.model_entity_id)
    sequence = _optional_text(record.sequence or record.uniprot_sequence)
    accessions = tuple(record.uniprot_accessions)
    if not accessions:
        accessions = (f"PROVISIONAL:{source_id}",)

    candidate_ids: list[str] = []
    if sequence:
        for accession in accessions:
            if accession.startswith("PROVISIONAL:"):
                protein = _upsert_protein(
                    proteins_by_key=proteins_by_key,
                    proteins_by_accession=proteins_by_accession,
                    source_provenance=source_provenance,
                    protein_id_internal=f"protein:alphafold:{source_id}",
                    primary_external_id_type="structure entity",
                    primary_external_id=source_id,
                    sequence=sequence,
                    protein_name=record.complex_name or source_id,
                    gene_name=record.gene[0] if record.gene else "",
                    organism_name=record.organism_scientific_name[0]
                    if record.organism_scientific_name
                    else "",
                    taxonomy_id=record.tax_id[0] if record.tax_id else None,
                    quality_flags=("provisional_identity", "alphafold_prediction"),
                )
                candidate_ids.append(protein.protein_id_internal)
            else:
                registry_candidates = _resolve_registry_candidates(registry, accession)
                if registry_candidates:
                    candidate_ids.extend(registry_candidates)
                else:
                    protein = _upsert_protein(
                        proteins_by_key=proteins_by_key,
                        proteins_by_accession=proteins_by_accession,
                        source_provenance=source_provenance,
                        protein_id_internal=f"protein:{accession}",
                        primary_external_id_type="UniProt accession",
                        primary_external_id=accession,
                        sequence=sequence,
                        protein_name=record.complex_name or source_id,
                        gene_name=record.gene[0] if record.gene else "",
                        organism_name=record.organism_scientific_name[0]
                        if record.organism_scientific_name
                        else "",
                        taxonomy_id=record.tax_id[0] if record.tax_id else None,
                        quality_flags=("alphafold_prediction",),
                    )
                    candidate_ids.append(protein.protein_id_internal)
    else:
        unresolved.append(
            UnresolvedStructureReference(
                reference_type="protein",
                reference_id=source_id,
                reason="missing_sequence",
                candidates=accessions,
                provenance_refs=(source_provenance.provenance_id,),
            )
        )

    chain_id_internal = f"chain:alphafold:{source_id}:{record.model_entity_id}"
    if len(candidate_ids) == 1:
        alignment = StructureAlignmentSummary(
            status="resolved",
            canonical_protein_internal_id=candidate_ids[0],
            observed_sequence_hash=_sequence_hash(_normalize_sequence(sequence))
            if sequence
            else None,
            identity=1.0 if sequence else None,
            notes=("predicted structure mapped by accession",),
        )
        mapped_protein_internal_id = candidate_ids[0]
        unresolved_ref = None
        quality_flags = ("protein_mapping_resolved", "predicted_structure")
    elif len(candidate_ids) > 1:
        alignment = StructureAlignmentSummary(
            status="ambiguous",
            observed_sequence_hash=_sequence_hash(_normalize_sequence(sequence))
            if sequence
            else None,
            candidates=tuple(candidate_ids),
            notes=("multiple candidate proteins preserved",),
        )
        mapped_protein_internal_id = None
        unresolved_ref = UnresolvedStructureReference(
            reference_type="chain",
            reference_id=chain_id_internal,
            reason="ambiguous_protein_mapping",
            candidates=tuple(candidate_ids),
            provenance_refs=(source_provenance.provenance_id,),
        )
        unresolved.append(unresolved_ref)
        quality_flags = ("protein_mapping_ambiguous", "predicted_structure")
    else:
        alignment = StructureAlignmentSummary(
            status="unresolved",
            observed_sequence_hash=_sequence_hash(_normalize_sequence(sequence))
            if sequence
            else None,
            notes=("no canonical protein candidate was available",),
        )
        mapped_protein_internal_id = None
        unresolved_ref = UnresolvedStructureReference(
            reference_type="chain",
            reference_id=chain_id_internal,
            reason="missing_primary_identifier",
            candidates=accessions,
            provenance_refs=(source_provenance.provenance_id,),
        )
        unresolved.append(unresolved_ref)
        quality_flags = ("protein_mapping_unresolved", "predicted_structure")

    chain = StructureChainRecord(
        chain_id_internal=chain_id_internal,
        structure_source="AlphaFold DB",
        structure_id=source_id,
        model_id=record.model_entity_id,
        chain_label=record.model_entity_id,
        mapped_protein_internal_id=mapped_protein_internal_id,
        extracted_sequence=sequence or "",
        sequence_alignment_to_canonical=alignment,
        mutation_summary=(),
        missing_residue_ranges=(),
        altloc_summary=(),
        confidence_summary=record.confidence.to_dict(),
        provenance_refs=(source_provenance.provenance_id,),
        quality_flags=quality_flags,
        unresolved_protein_reference=unresolved_ref,
        created_at=source_provenance.acquired_at,
        updated_at=source_provenance.acquired_at,
    )
    chains.append(chain)
    if mapped_protein_internal_id is not None:
        graph_edges.append(
            StructureGraphEdge(
                edge_id=f"edge:{mapped_protein_internal_id}->{chain.chain_id_internal}",
                source_id=mapped_protein_internal_id,
                target_id=chain.chain_id_internal,
                relation="protein_to_chain",
                provenance_refs=(source_provenance.provenance_id,),
            )
        )

    if record.structure_kind == "complex" and record.complex_composition:
        member_chain_ids: list[str] = []
        stoichiometry: dict[str, int] = {}
        for index, member in enumerate(record.complex_composition, start=1):
            member_chain_id = f"chain:alphafold:{source_id}:{record.model_entity_id}:member:{index}"
            member_chain_ids.append(member_chain_id)
            stoichiometry[member_chain_id] = member.stoichiometry
            member_sequence = sequence or ""
            member_accession = member.identifier
            if member_sequence:
                if member.identifier_type == "uniprotAccession":
                    _upsert_protein(
                        proteins_by_key=proteins_by_key,
                        proteins_by_accession=proteins_by_accession,
                        source_provenance=source_provenance,
                        protein_id_internal=f"protein:{member_accession}",
                        primary_external_id_type="UniProt accession",
                        primary_external_id=member_accession,
                        sequence=member_sequence,
                        protein_name=record.complex_name or source_id,
                        quality_flags=("alphafold_complex_member", "alphafold_prediction"),
                    )
                else:
                    _upsert_protein(
                        proteins_by_key=proteins_by_key,
                        proteins_by_accession=proteins_by_accession,
                        source_provenance=source_provenance,
                        protein_id_internal=f"protein:alphafold:{member_accession}",
                        primary_external_id_type="structure entity",
                        primary_external_id=member_accession,
                        sequence=member_sequence,
                        protein_name=record.complex_name or source_id,
                        quality_flags=("alphafold_complex_member", "alphafold_prediction"),
                    )
            graph_edges.append(
                StructureGraphEdge(
                    edge_id=f"edge:{chain.chain_id_internal}->{member_chain_id}",
                    source_id=chain.chain_id_internal,
                    target_id=member_chain_id,
                    relation="chain_to_complex",
                    provenance_refs=(source_provenance.provenance_id,),
                )
            )
        complexes.append(
            StructureComplexRecord(
                complex_id_internal=f"complex:alphafold:{source_id}:{record.model_entity_id}",
                complex_type="protein" if len(member_chain_ids) == 1 else "protein_protein",
                structure_source="AlphaFold DB",
                structure_id=source_id,
                member_chain_ids=tuple(member_chain_ids),
                stoichiometry=stoichiometry,
                biologically_relevant_flag=None,
                relevance_confidence=record.confidence.global_metric_value,
                extraction_notes=(
                    record.complex_name or "AlphaFold complex preserved without collapse",
                ),
                provenance_refs=(source_provenance.provenance_id,),
                quality_flags=("alphafold_prediction",),
                created_at=source_provenance.acquired_at,
                updated_at=source_provenance.acquired_at,
            )
        )

    _record_sequence_conflicts(
        proteins_by_key=proteins_by_key,
        conflicts=conflicts,
        source_provenance=source_provenance,
    )


def _record_sequence_conflicts(
    *,
    proteins_by_key: Mapping[tuple[str, str, str], StructureProteinRecord],
    conflicts: list[StructureIngestConflict],
    source_provenance: ProvenanceRecord,
) -> None:
    by_external_id: dict[str, list[StructureProteinRecord]] = {}
    for record in proteins_by_key.values():
        by_external_id.setdefault(record.primary_external_id, []).append(record)

    for external_id, records in by_external_id.items():
        if len(records) <= 1:
            continue
        sequence_values = tuple(
            dict.fromkeys(
                record.canonical_sequence for record in records if record.canonical_sequence
            )
        )
        if len(sequence_values) <= 1:
            continue
        conflicts.append(
            StructureIngestConflict(
                conflict_id=f"conflict:sequence:{external_id}",
                kind="sequence_conflict",
                subject_id=external_id,
                message=(
                    "structure ingest observed multiple distinct sequences for the same "
                    "primary identifier"
                ),
                observed_values={"sequences": sequence_values},
                provenance_refs=(source_provenance.provenance_id,),
                related_record_ids=tuple(record.protein_id_internal for record in records),
            )
        )


def _status_for_result(
    proteins: Sequence[StructureProteinRecord],
    chains: Sequence[StructureChainRecord],
    complexes: Sequence[StructureComplexRecord],
    unresolved: Sequence[UnresolvedStructureReference],
    conflicts: Sequence[StructureIngestConflict],
) -> StructureIngestStatus:
    if conflicts:
        return "conflict"
    if unresolved:
        if proteins or chains or complexes:
            return "partial"
        return "unresolved"
    return "resolved"


__all__ = [
    "StructureAlignmentStatus",
    "StructureAlignmentSummary",
    "StructureChainRecord",
    "StructureComplexRecord",
    "StructureConflictKind",
    "StructureGraphEdge",
    "StructureGraphRelation",
    "StructureIngestConflict",
    "StructureIngestResult",
    "StructureIngestStatus",
    "StructureProteinRecord",
    "UnresolvedStructureReference",
    "ingest_structure_bundle",
    "ingest_structure_records",
]
