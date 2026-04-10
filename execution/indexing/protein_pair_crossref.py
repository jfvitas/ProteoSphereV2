from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from core.canonical.registry import (
    CanonicalEntityRegistry,
    UnresolvedCanonicalReference,
)
from core.library.summary_record import (
    ProteinLigandSummaryRecord,
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecord,
    SummaryRecordContext,
    SummaryReference,
)
from core.storage.planning_index_schema import JoinStatus

CrossReferenceRecordKind = Literal["protein_protein", "protein_ligand"]

DEFAULT_CROSSREF_INDEX_GUIDANCE = (
    "index protein-protein and protein-ligand summaries by canonical protein and ligand ids",
    "keep unresolved participant references explicit instead of collapsing them into "
    "the nearest match",
)
DEFAULT_CROSSREF_STORAGE_GUIDANCE = (
    "treat this as a rebuildable feature-cache layer",
    "preserve provenance pointers and source evidence separately from canonical ids",
)
DEFAULT_CROSSREF_LAZY_GUIDANCE = (
    "defer heavy source evidence hydration until a candidate is selected",
    "keep protein and ligand identity separate from native pair provenance",
)
_SUPPORTED_PROTEIN_ACCESSION_RE = re.compile(r"^[A-Z0-9]{6,10}$")


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


def _unique_text(values: Iterable[Any]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _normalize_join_status(value: Any) -> JoinStatus:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    aliases: dict[str, JoinStatus] = {
        "unjoined": "unjoined",
        "candidate": "candidate",
        "joined": "joined",
        "partial": "partial",
        "ambiguous": "ambiguous",
        "conflict": "conflict",
        "deferred": "deferred",
        "lazy": "deferred",
    }
    status = aliases.get(text)
    if status is None:
        raise ValueError(f"unsupported join_status: {value!r}")
    return status


def _coerce_context(value: Any) -> SummaryRecordContext:
    if isinstance(value, SummaryRecordContext):
        return value
    if isinstance(value, Mapping):
        return SummaryRecordContext.from_dict(value)
    raise TypeError("context must be a SummaryRecordContext or mapping")


def _coerce_reference(value: Any) -> SummaryReference:
    if isinstance(value, SummaryReference):
        return value
    if isinstance(value, Mapping):
        return SummaryReference.from_dict(value)
    raise TypeError("references must contain SummaryReference objects or mappings")


def _coerce_provenance_pointer(value: Any) -> SummaryProvenancePointer:
    if isinstance(value, SummaryProvenancePointer):
        return value
    if isinstance(value, Mapping):
        return SummaryProvenancePointer.from_dict(value)
    raise TypeError(
        "provenance_pointers must contain SummaryProvenancePointer objects or mappings"
    )


def _coerce_unresolved_reference(value: Any) -> UnresolvedCanonicalReference:
    if isinstance(value, UnresolvedCanonicalReference):
        return value
    if isinstance(value, Mapping):
        return UnresolvedCanonicalReference(
            reference=value.get("reference") or "",
            entity_type=value.get("entity_type"),
            reason=value.get("reason") or "missing",
            candidates=tuple(value.get("candidates") or ()),
        )
    raise TypeError(
        "unresolved_references must contain UnresolvedCanonicalReference objects or mappings"
    )


def _explicit_canonical_reference(
    reference: str,
    *,
    entity_type: Literal["protein", "ligand"],
) -> str | None:
    text = _clean_text(reference)
    lowered = text.casefold()
    if entity_type == "protein":
        if lowered.startswith("protein:"):
            identifier = _clean_text(text.split(":", 1)[1]).upper()
            return f"protein:{identifier}" if identifier else None
        if lowered.startswith("uniprot:") or lowered.startswith("uniprotkb:"):
            identifier = _clean_text(text.split(":", 1)[1]).upper()
            return f"protein:{identifier}" if identifier else None
        accession = text.upper()
        if _SUPPORTED_PROTEIN_ACCESSION_RE.fullmatch(accession):
            return f"protein:{accession}"
        return None

    if lowered.startswith("ligand:"):
        identifier = _clean_text(text.split(":", 1)[1])
        return f"ligand:{identifier}" if identifier else None
    if lowered.startswith("bindingdb:"):
        identifier = _clean_text(text.split(":", 1)[1])
        return f"ligand:bindingdb:{identifier}" if identifier else None
    return None


def _resolve_reference(
    registry: CanonicalEntityRegistry | None,
    reference: str,
    *,
    entity_type: Literal["protein", "ligand"],
) -> tuple[str | None, UnresolvedCanonicalReference | None]:
    cleaned = _clean_text(reference)
    if not cleaned:
        return None, UnresolvedCanonicalReference(
            "<empty>",
            entity_type=entity_type,
            reason="empty_reference",
        )

    if registry is not None:
        resolved = registry.resolve(cleaned, entity_type=entity_type)
        if not isinstance(resolved, UnresolvedCanonicalReference):
            return registry.canonical_reference(resolved), None

        explicit = _explicit_canonical_reference(cleaned, entity_type=entity_type)
        if explicit is not None:
            return explicit, None
        return None, resolved

    explicit = _explicit_canonical_reference(cleaned, entity_type=entity_type)
    if explicit is not None:
        return explicit, None
    return None, UnresolvedCanonicalReference(
        cleaned,
        entity_type=entity_type,
        reason="missing",
    )


def _record_kind(record: SummaryRecord) -> CrossReferenceRecordKind:
    if isinstance(record, ProteinProteinSummaryRecord):
        return "protein_protein"
    if isinstance(record, ProteinLigandSummaryRecord):
        return "protein_ligand"
    raise TypeError("only protein-protein and protein-ligand summary records are supported")


def _coerce_summary_record(value: Any) -> SummaryRecord:
    if isinstance(value, (ProteinProteinSummaryRecord, ProteinLigandSummaryRecord)):
        return value
    if isinstance(value, ProteinSummaryRecord):
        raise TypeError("protein summary records are not part of the pair cross-reference index")
    if not isinstance(value, Mapping):
        raise TypeError("records must contain summary record objects or mappings")

    record_type = _clean_text(value.get("record_type") or value.get("type")).casefold()
    if record_type in {"protein_protein", "protein-protein", "pair", "interaction"}:
        return ProteinProteinSummaryRecord.from_dict(value)
    if record_type in {"protein_ligand", "protein-ligand", "ligand", "association"}:
        return ProteinLigandSummaryRecord.from_dict(value)
    if "protein_a_ref" in value and "protein_b_ref" in value:
        return ProteinProteinSummaryRecord.from_dict(value)
    if "protein_ref" in value and "ligand_ref" in value:
        return ProteinLigandSummaryRecord.from_dict(value)
    raise ValueError("unable to determine pair summary record type")


def _dedupe_unresolved(
    unresolved: Iterable[UnresolvedCanonicalReference],
) -> tuple[UnresolvedCanonicalReference, ...]:
    ordered: dict[tuple[str, str | None, str, tuple[str, ...]], UnresolvedCanonicalReference] = {}
    for item in unresolved:
        ordered.setdefault(
            (item.reference, item.entity_type, item.reason, item.candidates),
            item,
        )
    return tuple(ordered.values())


def _collect_source_evidence_refs(record: SummaryRecord) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(record, ProteinProteinSummaryRecord):
        values.extend(record.interaction_refs)
        if record.interaction_id is not None:
            values.append(record.interaction_id)
        values.extend(record.evidence_refs)
    elif isinstance(record, ProteinLigandSummaryRecord):
        values.extend(record.interaction_refs)
        if record.association_id is not None:
            values.append(record.association_id)
        values.extend(record.assay_refs)
    return _unique_text(values)


def _collect_provenance_pointers(record: SummaryRecord) -> tuple[SummaryProvenancePointer, ...]:
    return tuple(
        _coerce_provenance_pointer(pointer)
        for pointer in _iter_values(record.context.provenance_pointers)
    )


def _resolve_record_refs(
    record: SummaryRecord,
    *,
    registry: CanonicalEntityRegistry | None,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[UnresolvedCanonicalReference, ...],
]:
    protein_refs: list[str] = []
    ligand_refs: list[str] = []
    canonical_protein_ids: list[str] = []
    canonical_ligand_ids: list[str] = []
    unresolved: list[UnresolvedCanonicalReference] = []

    if isinstance(record, ProteinProteinSummaryRecord):
        for ref in (record.protein_a_ref, record.protein_b_ref):
            resolved, unresolved_ref = _resolve_reference(
                registry,
                ref,
                entity_type="protein",
            )
            protein_refs.append(_clean_text(ref))
            if resolved is not None:
                canonical_protein_ids.append(resolved)
            if unresolved_ref is not None:
                unresolved.append(unresolved_ref)
        return (
            _unique_text(protein_refs),
            (),
            _unique_text(canonical_protein_ids),
            (),
            _dedupe_unresolved(unresolved),
        )

    if isinstance(record, ProteinLigandSummaryRecord):
        resolved, unresolved_ref = _resolve_reference(
            registry,
            record.protein_ref,
            entity_type="protein",
        )
        protein_refs.append(_clean_text(record.protein_ref))
        if resolved is not None:
            canonical_protein_ids.append(resolved)
        if unresolved_ref is not None:
            unresolved.append(unresolved_ref)

        resolved, unresolved_ref = _resolve_reference(
            registry,
            record.ligand_ref,
            entity_type="ligand",
        )
        ligand_refs.append(_clean_text(record.ligand_ref))
        if resolved is not None:
            canonical_ligand_ids.append(resolved)
        if unresolved_ref is not None:
            unresolved.append(unresolved_ref)

        return (
            _unique_text(protein_refs),
            _unique_text(ligand_refs),
            _unique_text(canonical_protein_ids),
            _unique_text(canonical_ligand_ids),
            _dedupe_unresolved(unresolved),
        )

    raise TypeError("only protein-protein and protein-ligand records are supported")


def _join_status(
    record: SummaryRecord,
    unresolved_references: tuple[UnresolvedCanonicalReference, ...],
    *,
    has_resolved_proteins: bool,
    has_resolved_ligands: bool,
) -> JoinStatus:
    status = record.join_status
    reasons = {reference.reason for reference in unresolved_references}
    if "conflict" in reasons:
        return "conflict"
    if "ambiguous" in reasons:
        return "ambiguous"
    if "missing" in reasons:
        if has_resolved_proteins or has_resolved_ligands:
            if status == "joined":
                return "partial"
            return status
        return "unjoined"
    return status


def _pair_crossref_id(
    *,
    kind: CrossReferenceRecordKind,
    summary_id: str,
    canonical_protein_ids: tuple[str, ...],
    canonical_ligand_ids: tuple[str, ...],
) -> str:
    if kind == "protein_protein" and len(canonical_protein_ids) >= 2:
        return f"pair:{kind}:{canonical_protein_ids[0]}|{canonical_protein_ids[1]}"
    if kind == "protein_ligand" and canonical_protein_ids and canonical_ligand_ids:
        return f"pair:{kind}:{canonical_protein_ids[0]}|{canonical_ligand_ids[0]}"
    return f"pair:{kind}:{summary_id}"


@dataclass(frozen=True, slots=True)
class ProteinPairCrossReferenceRecord:
    summary_id: str
    record_type: CrossReferenceRecordKind
    protein_refs: tuple[str, ...]
    ligand_refs: tuple[str, ...] = ()
    canonical_protein_ids: tuple[str, ...] = ()
    canonical_ligand_ids: tuple[str, ...] = ()
    native_interaction_id: str | None = None
    native_association_id: str | None = None
    source_evidence_refs: tuple[str, ...] = ()
    provenance_pointers: tuple[SummaryProvenancePointer, ...] = ()
    unresolved_references: tuple[UnresolvedCanonicalReference, ...] = ()
    join_status: JoinStatus = "candidate"
    join_reason: str = ""
    context: SummaryRecordContext = field(default_factory=SummaryRecordContext)

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary_id", _clean_text(self.summary_id))
        object.__setattr__(self, "record_type", _record_kind_normalize(self.record_type))
        object.__setattr__(self, "protein_refs", _unique_text(self.protein_refs))
        object.__setattr__(self, "ligand_refs", _unique_text(self.ligand_refs))
        object.__setattr__(
            self,
            "canonical_protein_ids",
            _unique_text(self.canonical_protein_ids),
        )
        object.__setattr__(
            self,
            "canonical_ligand_ids",
            _unique_text(self.canonical_ligand_ids),
        )
        object.__setattr__(
            self,
            "native_interaction_id",
            _optional_text(self.native_interaction_id),
        )
        object.__setattr__(
            self,
            "native_association_id",
            _optional_text(self.native_association_id),
        )
        object.__setattr__(
            self,
            "source_evidence_refs",
            _unique_text(self.source_evidence_refs),
        )
        object.__setattr__(
            self,
            "provenance_pointers",
            tuple(
                _coerce_provenance_pointer(pointer)
                for pointer in _iter_values(self.provenance_pointers)
            ),
        )
        object.__setattr__(
            self,
            "unresolved_references",
            _dedupe_unresolved(
                _coerce_unresolved_reference(reference)
                for reference in _iter_values(self.unresolved_references)
            ),
        )
        object.__setattr__(self, "join_status", _normalize_join_status(self.join_status))
        object.__setattr__(self, "join_reason", _clean_text(self.join_reason))
        object.__setattr__(self, "context", _coerce_context(self.context))
        if not self.summary_id:
            raise ValueError("summary_id must not be empty")
        if not self.protein_refs:
            raise ValueError("protein_refs must not be empty")
        if self.record_type == "protein_protein" and len(self.protein_refs) < 2:
            raise ValueError("protein_protein records require two protein refs")
        if self.record_type == "protein_ligand" and not self.ligand_refs:
            raise ValueError("protein_ligand records require at least one ligand ref")

    @property
    def pair_id(self) -> str:
        return _pair_crossref_id(
            kind=self.record_type,
            summary_id=self.summary_id,
            canonical_protein_ids=self.canonical_protein_ids,
            canonical_ligand_ids=self.canonical_ligand_ids,
        )

    @property
    def source_record_ids(self) -> tuple[str, ...]:
        values: list[str] = [
            pointer.source_record_id or pointer.provenance_id
            for pointer in self.provenance_pointers
            if pointer.source_record_id or pointer.provenance_id
        ]
        values.extend(
            value for value in (self.native_interaction_id, self.native_association_id) if value
        )
        return _unique_text(values)

    @property
    def source_names(self) -> tuple[str, ...]:
        return _unique_text(pointer.source_name for pointer in self.provenance_pointers)

    @property
    def unresolved_count(self) -> int:
        return len(self.unresolved_references)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "summary_id": self.summary_id,
            "pair_id": self.pair_id,
            "protein_refs": list(self.protein_refs),
            "ligand_refs": list(self.ligand_refs),
            "canonical_protein_ids": list(self.canonical_protein_ids),
            "canonical_ligand_ids": list(self.canonical_ligand_ids),
            "native_interaction_id": self.native_interaction_id,
            "native_association_id": self.native_association_id,
            "source_evidence_refs": list(self.source_evidence_refs),
            "provenance_pointers": [pointer.to_dict() for pointer in self.provenance_pointers],
            "source_record_ids": list(self.source_record_ids),
            "source_names": list(self.source_names),
            "unresolved_references": [
                reference.to_dict() for reference in self.unresolved_references
            ],
            "join_status": self.join_status,
            "join_reason": self.join_reason,
            "context": self.context.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProteinPairCrossReferenceRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            summary_id=payload.get("summary_id") or payload.get("id") or "",
            record_type=payload.get("record_type") or payload.get("type") or "protein_protein",
            protein_refs=payload.get("protein_refs") or payload.get("protein_ref") or (),
            ligand_refs=payload.get("ligand_refs") or payload.get("ligand_ref") or (),
            canonical_protein_ids=payload.get("canonical_protein_ids")
            or payload.get("resolved_protein_ids")
            or (),
            canonical_ligand_ids=payload.get("canonical_ligand_ids")
            or payload.get("resolved_ligand_ids")
            or (),
            native_interaction_id=payload.get("native_interaction_id")
            or payload.get("interaction_id"),
            native_association_id=payload.get("native_association_id")
            or payload.get("association_id"),
            source_evidence_refs=payload.get("source_evidence_refs") or payload.get("evidence_refs")
            or (),
            provenance_pointers=payload.get("provenance_pointers") or (),
            unresolved_references=payload.get("unresolved_references") or (),
            join_status=payload.get("join_status") or payload.get("status") or "candidate",
            join_reason=payload.get("join_reason") or payload.get("reason") or "",
            context=payload.get("context") or {},
        )


def _record_type_normalize(value: Any) -> CrossReferenceRecordKind:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    aliases: dict[str, CrossReferenceRecordKind] = {
        "protein_protein": "protein_protein",
        "pair": "protein_protein",
        "interaction": "protein_protein",
        "protein_ligand": "protein_ligand",
        "association": "protein_ligand",
        "ligand": "protein_ligand",
    }
    kind = aliases.get(text)
    if kind is None:
        raise ValueError(f"unsupported record_type: {value!r}")
    return kind


def _entry_from_record(
    record: SummaryRecord,
    *,
    registry: CanonicalEntityRegistry | None,
) -> ProteinPairCrossReferenceRecord:
    kind = _record_kind(record)
    (
        protein_refs,
        ligand_refs,
        resolved_proteins,
        resolved_ligands,
        unresolved,
    ) = _resolve_record_refs(record, registry=registry)
    provenance_pointers = _collect_provenance_pointers(record)
    source_evidence_refs = _collect_source_evidence_refs(record)
    join_status = _join_status(
        record,
        unresolved,
        has_resolved_proteins=bool(resolved_proteins),
        has_resolved_ligands=bool(resolved_ligands),
    )

    return ProteinPairCrossReferenceRecord(
        summary_id=record.summary_id,
        record_type=kind,
        protein_refs=protein_refs,
        ligand_refs=ligand_refs,
        canonical_protein_ids=resolved_proteins,
        canonical_ligand_ids=resolved_ligands,
        native_interaction_id=getattr(record, "interaction_id", None),
        native_association_id=getattr(record, "association_id", None),
        source_evidence_refs=source_evidence_refs,
        provenance_pointers=provenance_pointers,
        unresolved_references=unresolved,
        join_status=join_status,
        join_reason=getattr(record, "join_reason", ""),
        context=record.context,
    )


def _records_from_input(records: object) -> tuple[SummaryRecord, ...]:
    if isinstance(records, SummaryLibrarySchema):
        return tuple(
            record
            for record in records.records
            if isinstance(record, (ProteinProteinSummaryRecord, ProteinLigandSummaryRecord))
        )
    if isinstance(records, (ProteinProteinSummaryRecord, ProteinLigandSummaryRecord)):
        return (records,)
    if isinstance(records, Mapping):
        if "record_type" in records or "type" in records:
            return (_coerce_summary_record(records),)
        if "records" in records or "summary_records" in records:
            library = SummaryLibrarySchema.from_dict(records)
            return _records_from_input(library)
        raise TypeError("records must be a summary library schema or pair summary record payload")
    if isinstance(records, Iterable) and not isinstance(records, (str, bytes)):
        normalized: list[SummaryRecord] = []
        for item in records:
            normalized.append(_coerce_summary_record(item))
        return tuple(normalized)
    raise TypeError("records must be a summary library schema or iterable of summary records")


def build_protein_pair_crossref_index(
    records: object,
    *,
    registry: CanonicalEntityRegistry | None = None,
    schema_version: int = 1,
) -> ProteinPairCrossReferenceIndex:
    if isinstance(records, ProteinPairCrossReferenceIndex):
        return records

    source_manifest_id = None
    if isinstance(records, SummaryLibrarySchema):
        source_manifest_id = records.source_manifest_id
    elif isinstance(records, Mapping) and "source_manifest_id" in records:
        source_manifest_id = _optional_text(records.get("source_manifest_id"))

    pair_records = sorted(
        (_entry_from_record(record, registry=registry) for record in _records_from_input(records)),
        key=lambda record: record.pair_id.casefold(),
    )
    return ProteinPairCrossReferenceIndex(
        library_id="protein_pair_crossref",
        records=tuple(pair_records),
        schema_version=schema_version,
        source_manifest_id=source_manifest_id,
        index_guidance=DEFAULT_CROSSREF_INDEX_GUIDANCE,
        storage_guidance=DEFAULT_CROSSREF_STORAGE_GUIDANCE,
        lazy_loading_guidance=DEFAULT_CROSSREF_LAZY_GUIDANCE,
    )


def build_protein_pair_cross_reference_index(
    records: object,
    *,
    registry: CanonicalEntityRegistry | None = None,
    schema_version: int = 1,
) -> ProteinPairCrossReferenceIndex:
    return build_protein_pair_crossref_index(
        records,
        registry=registry,
        schema_version=schema_version,
    )


@dataclass(frozen=True, slots=True)
class ProteinPairCrossReferenceIndex:
    library_id: str
    records: tuple[ProteinPairCrossReferenceRecord, ...]
    schema_version: int = 1
    source_manifest_id: str | None = None
    index_guidance: tuple[str, ...] = ()
    storage_guidance: tuple[str, ...] = ()
    lazy_loading_guidance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "library_id", _clean_text(self.library_id))
        object.__setattr__(self, "source_manifest_id", _optional_text(self.source_manifest_id))
        object.__setattr__(
            self,
            "index_guidance",
            _unique_text(self.index_guidance or DEFAULT_CROSSREF_INDEX_GUIDANCE),
        )
        object.__setattr__(
            self,
            "storage_guidance",
            _unique_text(self.storage_guidance or DEFAULT_CROSSREF_STORAGE_GUIDANCE),
        )
        object.__setattr__(
            self,
            "lazy_loading_guidance",
            _unique_text(self.lazy_loading_guidance or DEFAULT_CROSSREF_LAZY_GUIDANCE),
        )
        if not self.library_id:
            raise ValueError("library_id must not be empty")
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

        normalized_records: list[ProteinPairCrossReferenceRecord] = []
        seen_ids: set[str] = set()
        for record in self.records:
            if not isinstance(record, ProteinPairCrossReferenceRecord):
                raise TypeError("records must contain ProteinPairCrossReferenceRecord objects")
            if record.pair_id in seen_ids:
                raise ValueError(f"duplicate pair_id: {record.pair_id}")
            seen_ids.add(record.pair_id)
            normalized_records.append(record)
        object.__setattr__(self, "records", tuple(normalized_records))

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def pair_records(self) -> tuple[ProteinPairCrossReferenceRecord, ...]:
        return self.records

    @property
    def unresolved_count(self) -> int:
        return sum(record.unresolved_count for record in self.records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "library_id": self.library_id,
            "schema_version": self.schema_version,
            "source_manifest_id": self.source_manifest_id,
            "record_count": self.record_count,
            "index_guidance": list(self.index_guidance),
            "storage_guidance": list(self.storage_guidance),
            "lazy_loading_guidance": list(self.lazy_loading_guidance),
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProteinPairCrossReferenceIndex:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            library_id=payload.get("library_id") or payload.get("id") or "protein_pair_crossref",
            records=tuple(
                item
                if isinstance(item, ProteinPairCrossReferenceRecord)
                else ProteinPairCrossReferenceRecord.from_dict(item)
                for item in _iter_values(
                    payload.get("records") or payload.get("summary_records") or ()
                )
            ),
            schema_version=int(payload.get("schema_version") or 1),
            source_manifest_id=payload.get("source_manifest_id") or payload.get("manifest_id"),
            index_guidance=payload.get("index_guidance") or payload.get("index_notes") or (),
            storage_guidance=payload.get("storage_guidance") or payload.get("storage_notes") or (),
            lazy_loading_guidance=payload.get("lazy_loading_guidance")
            or payload.get("lazy_guidance")
            or (),
        )


def _record_kind_normalize(value: Any) -> CrossReferenceRecordKind:
    return _record_type_normalize(value)


ProteinPairCrossReferenceEntry = ProteinPairCrossReferenceRecord
ProteinPairCrossReferenceSchema = ProteinPairCrossReferenceIndex
ProteinPairCrossRefEntry = ProteinPairCrossReferenceRecord
ProteinPairCrossRefIndex = ProteinPairCrossReferenceIndex


__all__ = [
    "DEFAULT_CROSSREF_INDEX_GUIDANCE",
    "DEFAULT_CROSSREF_LAZY_GUIDANCE",
    "DEFAULT_CROSSREF_STORAGE_GUIDANCE",
    "CrossReferenceRecordKind",
    "ProteinPairCrossRefEntry",
    "ProteinPairCrossRefIndex",
    "ProteinPairCrossReferenceEntry",
    "ProteinPairCrossReferenceIndex",
    "ProteinPairCrossReferenceRecord",
    "ProteinPairCrossReferenceSchema",
    "build_protein_pair_cross_reference_index",
    "build_protein_pair_crossref_index",
]
