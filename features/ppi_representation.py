from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from core.canonical.registry import CanonicalEntityRegistry, UnresolvedCanonicalReference
from core.library.summary_record import (
    ProteinLigandSummaryRecord,
    ProteinProteinSummaryRecord,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
)
from execution.indexing.protein_pair_crossref import (
    ProteinPairCrossReferenceIndex,
    ProteinPairCrossReferenceRecord,
)

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | tuple["JSONValue", ...] | dict[str, "JSONValue"]

PPIRepresentationStatus = Literal["ready", "partial", "unresolved"]
PPIRepresentationIssueKind = Literal[
    "skipped_non_ppi_record",
    "missing_protein_reference",
    "unresolved_protein_reference",
]

DEFAULT_PPI_FEATURE_NAMES = (
    "pair_id",
    "summary_id",
    "protein_a_ref",
    "protein_b_ref",
    "canonical_protein_a_id",
    "canonical_protein_b_id",
    "canonical_protein_count",
    "interaction_type",
    "physical_interaction",
    "directionality",
    "evidence_count",
    "confidence",
    "interaction_ref_count",
    "evidence_ref_count",
    "provenance_pointer_count",
    "cross_reference_count",
    "materialization_pointer_count",
    "storage_tier",
)

DEFAULT_PPI_INDEX_GUIDANCE = (
    "preserve protein-pair ordering in source refs while keeping a stable pair key",
    "keep unresolved protein references explicit instead of collapsing them",
    "treat this layer as a rebuildable feature representation for pair models",
)
DEFAULT_PPI_STORAGE_GUIDANCE = (
    "keep pair identity and summary provenance separate from feature values",
    "defer heavy source payloads until a pair example is selected",
)
DEFAULT_PPI_LAZY_GUIDANCE = (
    "hydrate only the summary fields needed for pair modeling",
    "retain unresolved references and provenance pointers for later inspection",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _unique_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_json_value(value: Any, field_name: str) -> JSONValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, JSONValue] = {}
        for key, item in value.items():
            normalized_key = _required_text(key, f"{field_name} key")
            normalized[normalized_key] = _normalize_json_value(
                item,
                f"{field_name}[{normalized_key!r}]",
            )
        return normalized
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return tuple(_normalize_json_value(item, field_name) for item in value)
    raise TypeError(f"{field_name} must contain only JSON-serializable values")


def _normalize_json_mapping(
    value: Mapping[str, Any] | None,
    field_name: str,
) -> dict[str, JSONValue]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    normalized: dict[str, JSONValue] = {}
    for key, item in value.items():
        normalized_key = _required_text(key, f"{field_name} key")
        normalized[normalized_key] = _normalize_json_value(
            item,
            f"{field_name}[{normalized_key!r}]",
        )
    return normalized


def _json_ready(value: JSONValue) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _normalize_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    text = _clean_text(value).casefold()
    if text in {"true", "yes", "y", "1"}:
        return True
    if text in {"false", "no", "n", "0"}:
        return False
    raise TypeError("value must be a boolean or boolean-like string")


def _normalize_float(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric or None")
    return float(value)


def _pair_key(*refs: str) -> str:
    cleaned = sorted(text for text in (_clean_text(ref) for ref in refs) if text)
    return "|".join(cleaned)


def _canonical_protein_ref(reference: str) -> str | None:
    cleaned = _clean_text(reference)
    if not cleaned:
        return None
    lowered = cleaned.casefold()
    if lowered.startswith("protein:"):
        identifier = _clean_text(cleaned.split(":", 1)[1])
        return f"protein:{identifier}" if identifier else None
    if lowered.startswith("uniprot:") or lowered.startswith("uniprotkb:"):
        identifier = _clean_text(cleaned.split(":", 1)[1]).upper()
        return f"protein:{identifier}" if identifier else None
    return None


def _resolve_protein_reference(
    registry: CanonicalEntityRegistry | None,
    reference: str,
) -> tuple[str | None, UnresolvedCanonicalReference | None]:
    cleaned = _clean_text(reference)
    if not cleaned:
        return None, UnresolvedCanonicalReference(
            reference="<empty>",
            entity_type="protein",
            reason="empty_reference",
        )
    if registry is not None:
        resolved = registry.resolve(cleaned, entity_type="protein")
        if not isinstance(resolved, UnresolvedCanonicalReference):
            return registry.canonical_reference(resolved), None
        explicit = _canonical_protein_ref(cleaned)
        if explicit is not None:
            return explicit, None
        return None, resolved
    explicit = _canonical_protein_ref(cleaned)
    if explicit is not None:
        return explicit, None
    return None, UnresolvedCanonicalReference(
        reference=cleaned,
        entity_type="protein",
        reason="missing",
    )


def _coerce_provenance_pointer(value: Any) -> SummaryProvenancePointer:
    if isinstance(value, SummaryProvenancePointer):
        return value
    if isinstance(value, Mapping):
        return SummaryProvenancePointer.from_dict(value)
    raise TypeError("provenance pointers must contain SummaryProvenancePointer objects or mappings")


def _coerce_context(value: Any) -> SummaryRecordContext:
    if isinstance(value, SummaryRecordContext):
        return value
    if isinstance(value, Mapping):
        return SummaryRecordContext.from_dict(value)
    raise TypeError("context must be a SummaryRecordContext or mapping")


def _coerce_record(value: Any) -> ProteinProteinSummaryRecord | ProteinPairCrossReferenceRecord:
    if isinstance(
        value,
        (ProteinProteinSummaryRecord, ProteinLigandSummaryRecord, ProteinPairCrossReferenceRecord),
    ):
        return value
    if isinstance(value, Mapping):
        record_type = _clean_text(value.get("record_type") or value.get("type")).casefold()
        if (
            "protein_refs" in value
            or "canonical_protein_ids" in value
            or "unresolved_references" in value
        ):
            return ProteinPairCrossReferenceRecord.from_dict(value)
        if record_type in {"protein_ligand", "protein-ligand", "ligand", "association"}:
            return ProteinLigandSummaryRecord.from_dict(value)
        if record_type in {"protein_protein", "protein-protein", "pair", "interaction"}:
            return ProteinProteinSummaryRecord.from_dict(value)
        if "protein_a_ref" in value and "protein_b_ref" in value:
            return ProteinProteinSummaryRecord.from_dict(value)
    raise TypeError(
        "records must contain protein-protein summary records or pair cross-reference records"
    )


def _coerce_input_records(
    records: object,
) -> tuple[ProteinProteinSummaryRecord | ProteinPairCrossReferenceRecord, ...]:
    if isinstance(records, SummaryLibrarySchema):
        return tuple(records.records)
    if isinstance(records, ProteinPairCrossReferenceIndex):
        return tuple(records.records)
    if isinstance(records, Mapping) and ("records" in records or "summary_records" in records):
        library = SummaryLibrarySchema.from_dict(records)
        return tuple(library.records)
    if isinstance(records, Iterable) and not isinstance(records, (str, bytes)):
        return tuple(_coerce_record(item) for item in records)
    return (_coerce_record(records),)


@dataclass(frozen=True, slots=True)
class PPIRepresentationIssue:
    pair_id: str
    kind: PPIRepresentationIssueKind
    message: str
    summary_id: str | None = None
    protein_ref: str | None = None
    details: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "pair_id", _required_text(self.pair_id, "pair_id"))
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(self, "summary_id", _optional_text(self.summary_id))
        object.__setattr__(self, "protein_ref", _optional_text(self.protein_ref))
        object.__setattr__(self, "details", _normalize_json_mapping(self.details, "details"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "kind": self.kind,
            "message": self.message,
            "summary_id": self.summary_id,
            "protein_ref": self.protein_ref,
            "details": _json_ready(dict(self.details)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PPIRepresentationIssue:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            pair_id=payload.get("pair_id") or payload.get("id") or "",
            kind=payload.get("kind") or "missing_protein_reference",
            message=payload.get("message") or "",
            summary_id=payload.get("summary_id") or payload.get("record_id"),
            protein_ref=payload.get("protein_ref") or payload.get("protein"),
            details=payload.get("details") or payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class PPIRepresentationRecord:
    summary_id: str
    pair_id: str
    protein_a_ref: str
    protein_b_ref: str
    canonical_protein_ids: tuple[str, ...]
    provenance_pointers: tuple[SummaryProvenancePointer, ...]
    context: SummaryRecordContext
    interaction_type: str = ""
    interaction_id: str | None = None
    interaction_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    organism_name: str = ""
    taxon_id: int | None = None
    physical_interaction: bool | None = None
    directionality: str | None = None
    evidence_count: int | None = None
    confidence: float | None = None
    join_status: str = "joined"
    join_reason: str = ""
    source_evidence_refs: tuple[str, ...] = ()
    unresolved_references: tuple[UnresolvedCanonicalReference, ...] = ()
    feature_values: Mapping[str, JSONValue] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary_id", _required_text(self.summary_id, "summary_id"))
        object.__setattr__(self, "pair_id", _required_text(self.pair_id, "pair_id"))
        object.__setattr__(
            self,
            "protein_a_ref",
            _required_text(self.protein_a_ref, "protein_a_ref"),
        )
        object.__setattr__(
            self,
            "protein_b_ref",
            _required_text(self.protein_b_ref, "protein_b_ref"),
        )
        object.__setattr__(self, "canonical_protein_ids", _unique_text(self.canonical_protein_ids))
        object.__setattr__(self, "provenance_pointers", tuple(self.provenance_pointers))
        object.__setattr__(self, "context", _coerce_context(self.context))
        object.__setattr__(self, "interaction_type", _clean_text(self.interaction_type))
        object.__setattr__(self, "interaction_id", _optional_text(self.interaction_id))
        object.__setattr__(self, "interaction_refs", _unique_text(self.interaction_refs))
        object.__setattr__(self, "evidence_refs", _unique_text(self.evidence_refs))
        object.__setattr__(self, "organism_name", _clean_text(self.organism_name))
        object.__setattr__(
            self, "taxon_id", int(self.taxon_id) if self.taxon_id is not None else None
        )
        object.__setattr__(self, "physical_interaction", _normalize_bool(self.physical_interaction))
        object.__setattr__(self, "directionality", _optional_text(self.directionality))
        object.__setattr__(
            self,
            "evidence_count",
            int(self.evidence_count) if self.evidence_count is not None else None,
        )
        object.__setattr__(self, "confidence", _normalize_float(self.confidence, "confidence"))
        object.__setattr__(self, "join_status", _clean_text(self.join_status) or "joined")
        object.__setattr__(self, "join_reason", _clean_text(self.join_reason))
        object.__setattr__(self, "source_evidence_refs", _unique_text(self.source_evidence_refs))
        object.__setattr__(self, "unresolved_references", tuple(self.unresolved_references))
        object.__setattr__(
            self,
            "feature_values",
            _normalize_json_mapping(self.feature_values, "feature_values"),
        )
        object.__setattr__(self, "notes", _unique_text(self.notes))

    @property
    def feature_names(self) -> tuple[str, ...]:
        return DEFAULT_PPI_FEATURE_NAMES

    @property
    def feature_vector(self) -> tuple[Any, ...]:
        values = dict(self.feature_values)
        return tuple(values.get(name) for name in self.feature_names)

    @property
    def source_record_ids(self) -> tuple[str, ...]:
        return tuple(
            pointer.source_record_id
            for pointer in self.provenance_pointers
            if pointer.source_record_id is not None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "pair_id": self.pair_id,
            "protein_a_ref": self.protein_a_ref,
            "protein_b_ref": self.protein_b_ref,
            "canonical_protein_ids": list(self.canonical_protein_ids),
            "provenance_pointers": [pointer.to_dict() for pointer in self.provenance_pointers],
            "source_record_ids": list(self.source_record_ids),
            "context": self.context.to_dict(),
            "interaction_type": self.interaction_type,
            "interaction_id": self.interaction_id,
            "interaction_refs": list(self.interaction_refs),
            "evidence_refs": list(self.evidence_refs),
            "organism_name": self.organism_name,
            "taxon_id": self.taxon_id,
            "physical_interaction": self.physical_interaction,
            "directionality": self.directionality,
            "evidence_count": self.evidence_count,
            "confidence": self.confidence,
            "join_status": self.join_status,
            "join_reason": self.join_reason,
            "source_evidence_refs": list(self.source_evidence_refs),
            "unresolved_references": [
                reference.to_dict() for reference in self.unresolved_references
            ],
            "feature_names": list(self.feature_names),
            "feature_vector": list(self.feature_vector),
            "feature_values": _json_ready(dict(self.feature_values)),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PPIRepresentationRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            summary_id=payload.get("summary_id") or payload.get("id") or "",
            pair_id=payload.get("pair_id") or payload.get("pair") or "",
            protein_a_ref=payload.get("protein_a_ref") or payload.get("left_ref") or "",
            protein_b_ref=payload.get("protein_b_ref") or payload.get("right_ref") or "",
            canonical_protein_ids=payload.get("canonical_protein_ids")
            or payload.get("canonical_ids")
            or (),
            provenance_pointers=tuple(
                _coerce_provenance_pointer(pointer)
                for pointer in _iter_values(
                    payload.get("provenance_pointers") or payload.get("provenance") or ()
                )
            ),
            context=_coerce_context(payload.get("context") or {}),
            interaction_type=payload.get("interaction_type") or payload.get("kind") or "",
            interaction_id=payload.get("interaction_id") or payload.get("pair_id"),
            interaction_refs=payload.get("interaction_refs") or (),
            evidence_refs=payload.get("evidence_refs") or payload.get("source_evidence_refs") or (),
            organism_name=payload.get("organism_name") or payload.get("organism") or "",
            taxon_id=payload.get("taxon_id") or payload.get("tax_id"),
            physical_interaction=payload.get("physical_interaction"),
            directionality=payload.get("directionality"),
            evidence_count=payload.get("evidence_count"),
            confidence=payload.get("confidence"),
            join_status=payload.get("join_status") or "joined",
            join_reason=payload.get("join_reason") or payload.get("reason") or "",
            source_evidence_refs=payload.get("source_evidence_refs")
            or payload.get("evidence_refs")
            or (),
            unresolved_references=tuple(
                UnresolvedCanonicalReference(
                    reference=item.get("reference") or "",
                    entity_type=item.get("entity_type"),
                    reason=item.get("reason") or "missing",
                    candidates=tuple(item.get("candidates") or ()),
                )
                for item in _iter_values(payload.get("unresolved_references") or ())
                if isinstance(item, Mapping)
            ),
            feature_values=payload.get("feature_values") or payload.get("features") or {},
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class PPIRepresentation:
    representation_id: str
    records: tuple[PPIRepresentationRecord, ...]
    status: PPIRepresentationStatus
    source_manifest_id: str | None = None
    library_id: str = "ppi-representation"
    schema_version: int = 1
    index_guidance: tuple[str, ...] = field(default_factory=tuple)
    storage_guidance: tuple[str, ...] = field(default_factory=tuple)
    lazy_loading_guidance: tuple[str, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)
    issues: tuple[PPIRepresentationIssue, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "representation_id", _required_text(self.representation_id, "representation_id")
        )
        object.__setattr__(self, "source_manifest_id", _optional_text(self.source_manifest_id))
        object.__setattr__(self, "library_id", _required_text(self.library_id, "library_id"))
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        if self.status not in {"ready", "partial", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")
        records = []
        seen: set[str] = set()
        for record in self.records:
            if not isinstance(record, PPIRepresentationRecord):
                raise TypeError("records must contain PPIRepresentationRecord objects")
            if record.pair_id in seen:
                raise ValueError(f"duplicate pair_id: {record.pair_id}")
            seen.add(record.pair_id)
            records.append(record)
        object.__setattr__(
            self, "records", tuple(sorted(records, key=lambda item: item.pair_id.casefold()))
        )
        object.__setattr__(
            self, "index_guidance", _unique_text(self.index_guidance or DEFAULT_PPI_INDEX_GUIDANCE)
        )
        object.__setattr__(
            self,
            "storage_guidance",
            _unique_text(self.storage_guidance or DEFAULT_PPI_STORAGE_GUIDANCE),
        )
        object.__setattr__(
            self,
            "lazy_loading_guidance",
            _unique_text(self.lazy_loading_guidance or DEFAULT_PPI_LAZY_GUIDANCE),
        )
        object.__setattr__(self, "provenance", _unique_text(self.provenance))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "notes", _unique_text(self.notes))

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def pair_ids(self) -> tuple[str, ...]:
        return tuple(record.pair_id for record in self.records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "representation_id": self.representation_id,
            "library_id": self.library_id,
            "source_manifest_id": self.source_manifest_id,
            "status": self.status,
            "record_count": self.record_count,
            "pair_ids": list(self.pair_ids),
            "records": [record.to_dict() for record in self.records],
            "index_guidance": list(self.index_guidance),
            "storage_guidance": list(self.storage_guidance),
            "lazy_loading_guidance": list(self.lazy_loading_guidance),
            "provenance": list(self.provenance),
            "issues": [issue.to_dict() for issue in self.issues],
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PPIRepresentation:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            representation_id=payload.get("representation_id") or payload.get("id") or "",
            records=tuple(
                item
                if isinstance(item, PPIRepresentationRecord)
                else PPIRepresentationRecord.from_dict(item)
                for item in _iter_values(payload.get("records") or payload.get("entries") or ())
            ),
            status=payload.get("status") or "unresolved",
            source_manifest_id=payload.get("source_manifest_id")
            or payload.get("manifest_id")
            or payload.get("source_manifest"),
            library_id=payload.get("library_id") or payload.get("library") or "ppi-representation",
            schema_version=int(payload.get("schema_version") or 1),
            index_guidance=payload.get("index_guidance") or payload.get("guidance") or (),
            storage_guidance=payload.get("storage_guidance") or (),
            lazy_loading_guidance=payload.get("lazy_loading_guidance") or (),
            provenance=payload.get("provenance") or (),
            issues=tuple(
                PPIRepresentationIssue.from_dict(item)
                for item in _iter_values(payload.get("issues") or ())
            ),
            notes=payload.get("notes") or (),
        )


def _record_pair_id(pair_refs: tuple[str, ...]) -> str:
    return f"pair:protein_protein:{_pair_key(*pair_refs[:2])}"


def _record_source_pointers(
    record: ProteinProteinSummaryRecord | ProteinPairCrossReferenceRecord,
) -> tuple[SummaryProvenancePointer, ...]:
    if isinstance(record, ProteinPairCrossReferenceRecord):
        return tuple(record.provenance_pointers)
    return tuple(
        _coerce_provenance_pointer(pointer)
        for pointer in _iter_values(record.context.provenance_pointers)
    )


def _record_context(
    record: ProteinProteinSummaryRecord | ProteinPairCrossReferenceRecord,
) -> SummaryRecordContext:
    if isinstance(record, ProteinPairCrossReferenceRecord):
        return record.context
    return record.context


def _record_unresolved(
    record: ProteinProteinSummaryRecord | ProteinPairCrossReferenceRecord,
) -> tuple[UnresolvedCanonicalReference, ...]:
    if isinstance(record, ProteinPairCrossReferenceRecord):
        return tuple(record.unresolved_references)
    return ()


def _feature_values(
    *,
    pair_id: str,
    record: ProteinProteinSummaryRecord | ProteinPairCrossReferenceRecord,
    canonical_protein_ids: tuple[str, ...],
    provenance_pointers: tuple[SummaryProvenancePointer, ...],
    context: SummaryRecordContext,
) -> dict[str, JSONValue]:
    canonical_a = canonical_protein_ids[0] if canonical_protein_ids else None
    canonical_b = canonical_protein_ids[1] if len(canonical_protein_ids) > 1 else None
    return {
        "pair_id": pair_id,
        "summary_id": record.summary_id,
        "protein_a_ref": record.protein_refs[0]
        if isinstance(record, ProteinPairCrossReferenceRecord)
        else record.protein_a_ref,
        "protein_b_ref": record.protein_refs[1]
        if isinstance(record, ProteinPairCrossReferenceRecord)
        else record.protein_b_ref,
        "canonical_protein_a_id": canonical_a,
        "canonical_protein_b_id": canonical_b,
        "canonical_protein_count": len(canonical_protein_ids),
        "interaction_type": getattr(record, "interaction_type", "")
        or getattr(record, "association_type", ""),
        "physical_interaction": getattr(record, "physical_interaction", None),
        "directionality": getattr(record, "directionality", None),
        "evidence_count": getattr(record, "evidence_count", None),
        "confidence": getattr(record, "confidence", None),
        "interaction_ref_count": len(getattr(record, "interaction_refs", ())),
        "evidence_ref_count": len(
            getattr(record, "evidence_refs", ())
            if isinstance(record, ProteinProteinSummaryRecord)
            else getattr(record, "assay_refs", ())
        ),
        "provenance_pointer_count": len(provenance_pointers),
        "cross_reference_count": len(context.cross_references),
        "materialization_pointer_count": len(context.materialization_pointers),
        "storage_tier": context.storage_tier,
    }


def _representation_record_from_summary(
    record: ProteinProteinSummaryRecord | ProteinPairCrossReferenceRecord,
    *,
    registry: CanonicalEntityRegistry | None = None,
) -> tuple[PPIRepresentationRecord, tuple[PPIRepresentationIssue, ...]]:
    if isinstance(record, ProteinPairCrossReferenceRecord):
        protein_refs = record.protein_refs
        canonical_ids = record.canonical_protein_ids
        unresolved_references = record.unresolved_references
        evidence_refs = record.evidence_refs if hasattr(record, "evidence_refs") else ()
    else:
        protein_refs = (record.protein_a_ref, record.protein_b_ref)
        canonical_a, unresolved_a = _resolve_protein_reference(registry, record.protein_a_ref)
        canonical_b, unresolved_b = _resolve_protein_reference(registry, record.protein_b_ref)
        canonical_ids = tuple(value for value in (canonical_a, canonical_b) if value is not None)
        unresolved_references = tuple(
            value for value in (unresolved_a, unresolved_b) if value is not None
        )
        evidence_refs = record.evidence_refs

    pair_id = _record_pair_id(canonical_ids or protein_refs)
    provenance_pointers = _record_source_pointers(record)
    context = _record_context(record)
    issues: list[PPIRepresentationIssue] = []

    for unresolved in unresolved_references:
        issues.append(
            PPIRepresentationIssue(
                pair_id=pair_id,
                kind="unresolved_protein_reference",
                message="selected PPI record includes an unresolved protein reference",
                summary_id=record.summary_id,
                protein_ref=unresolved.reference,
                details={
                    "entity_type": unresolved.entity_type,
                    "reason": unresolved.reason,
                    "candidates": unresolved.candidates,
                },
            )
        )

    if not canonical_ids:
        issues.append(
            PPIRepresentationIssue(
                pair_id=pair_id,
                kind="missing_protein_reference",
                message="selected PPI record did not resolve any canonical protein ids",
                summary_id=record.summary_id,
                details={
                    "protein_refs": protein_refs,
                },
            )
        )

    representation_record = PPIRepresentationRecord(
        summary_id=record.summary_id,
        pair_id=pair_id,
        protein_a_ref=protein_refs[0],
        protein_b_ref=protein_refs[1],
        canonical_protein_ids=canonical_ids,
        provenance_pointers=provenance_pointers,
        context=context,
        interaction_type=getattr(record, "interaction_type", "")
        or getattr(record, "association_type", ""),
        interaction_id=getattr(record, "interaction_id", None),
        interaction_refs=getattr(record, "interaction_refs", ()),
        evidence_refs=evidence_refs,
        organism_name=getattr(record, "organism_name", ""),
        taxon_id=getattr(record, "taxon_id", None),
        physical_interaction=getattr(record, "physical_interaction", None),
        directionality=getattr(record, "directionality", None),
        evidence_count=getattr(record, "evidence_count", None),
        confidence=getattr(record, "confidence", None),
        join_status=getattr(record, "join_status", "joined"),
        join_reason=getattr(record, "join_reason", ""),
        source_evidence_refs=getattr(record, "source_evidence_refs", evidence_refs),
        unresolved_references=unresolved_references,
        feature_values=_feature_values(
            pair_id=pair_id,
            record=record,
            canonical_protein_ids=canonical_ids,
            provenance_pointers=provenance_pointers,
            context=context,
        ),
        notes=getattr(record, "notes", ()),
    )
    return representation_record, tuple(issues)


def build_ppi_representation(
    records: object,
    *,
    registry: CanonicalEntityRegistry | None = None,
    representation_id: str = "ppi-representation",
    library_id: str = "ppi-representation",
    source_manifest_id: str | None = None,
    schema_version: int = 1,
    index_guidance: Iterable[str] = (),
    storage_guidance: Iterable[str] = (),
    lazy_loading_guidance: Iterable[str] = (),
    provenance: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> PPIRepresentation:
    input_records = _coerce_input_records(records)

    if isinstance(records, SummaryLibrarySchema) and source_manifest_id is None:
        source_manifest_id = records.source_manifest_id
    elif isinstance(records, Mapping) and source_manifest_id is None:
        source_manifest_id = _optional_text(records.get("source_manifest_id"))

    representation_records: list[PPIRepresentationRecord] = []
    issues: list[PPIRepresentationIssue] = []
    for record in input_records:
        if not isinstance(record, (ProteinProteinSummaryRecord, ProteinPairCrossReferenceRecord)):
            issues.append(
                PPIRepresentationIssue(
                    pair_id="pair:protein_protein:skipped",
                    kind="skipped_non_ppi_record",
                    message=(
                        "non-protein-protein summary records are not part of the PPI representation"
                    ),
                    summary_id=getattr(record, "summary_id", None),
                    details={"record_type": getattr(record, "record_type", None)},
                )
            )
            continue
        representation_record, record_issues = _representation_record_from_summary(
            record,
            registry=registry,
        )
        representation_records.append(representation_record)
        issues.extend(record_issues)

    status: PPIRepresentationStatus
    if issues and representation_records:
        status = "partial"
    elif issues:
        status = "unresolved"
    else:
        status = "ready"

    provenance_refs = _unique_text(provenance)
    if source_manifest_id is not None:
        provenance_refs = _unique_text((source_manifest_id, *provenance_refs))

    return PPIRepresentation(
        representation_id=representation_id,
        records=tuple(representation_records),
        status=status,
        source_manifest_id=source_manifest_id,
        library_id=library_id,
        schema_version=schema_version,
        index_guidance=tuple(index_guidance),
        storage_guidance=tuple(storage_guidance),
        lazy_loading_guidance=tuple(lazy_loading_guidance),
        provenance=provenance_refs,
        issues=tuple(issues),
        notes=tuple(notes),
    )


def validate_ppi_representation_payload(payload: Mapping[str, Any]) -> PPIRepresentation:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return PPIRepresentation.from_dict(payload)


__all__ = [
    "DEFAULT_PPI_FEATURE_NAMES",
    "PPIRepresentation",
    "PPIRepresentationIssue",
    "PPIRepresentationIssueKind",
    "PPIRepresentationRecord",
    "PPIRepresentationStatus",
    "build_ppi_representation",
    "validate_ppi_representation_payload",
]
