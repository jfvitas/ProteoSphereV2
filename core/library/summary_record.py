from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from core.storage.planning_index_schema import (
    JoinStatus,
    PlanningIndexMaterializationPointer,
)

SummaryRecordKind = Literal[
    "protein",
    "protein_variant",
    "structure_unit",
    "protein_protein",
    "protein_ligand",
]
SummaryReferenceKind = Literal["cross_reference", "motif", "domain", "pathway"]
SummaryStorageTier = Literal[
    "planning_index",
    "canonical_store",
    "feature_cache",
    "deferred_fetch",
    "scrape_only",
]

DEFAULT_PROTEIN_PLANNING_KEYS = (
    "accession",
    "reviewed",
    "organism",
    "sequence_length",
    "sequence_version",
    "mnemonic",
    "proteome_membership",
    "cross_reference_namespaces",
)
DEFAULT_PROTEIN_DEFERRED_PAYLOADS = (
    "long_comments",
    "evidence_text",
    "rare_isoforms",
    "full_annotation_payload",
)
DEFAULT_PROTEIN_LAZY_GUIDANCE = (
    "preload accession, review status, organism, and cross-reference namespaces",
    "defer long comments, evidence text, and rare isoforms until selection",
)
DEFAULT_PAIR_PLANNING_KEYS = (
    "protein_a_ref",
    "protein_b_ref",
    "interaction_id",
    "interaction_type",
    "organism",
    "physical_vs_genetic",
    "evidence_count",
)
DEFAULT_PAIR_DEFERRED_PAYLOADS = (
    "full_interaction_row",
    "publication_context",
    "complex_projection_payload",
)
DEFAULT_PAIR_LAZY_GUIDANCE = (
    "preserve native complex lineage and directionality",
    "do not flatten n-ary evidence into binary edges without lineage",
)
DEFAULT_LIGAND_PLANNING_KEYS = (
    "protein_ref",
    "ligand_ref",
    "assay_id",
    "interaction_id",
    "organism",
    "chemical_identifier",
    "target_join_status",
)
DEFAULT_LIGAND_DEFERRED_PAYLOADS = (
    "full_assay_rows",
    "assay_text",
    "publication_context",
)
DEFAULT_LIGAND_LAZY_GUIDANCE = (
    "keep target and ligand identity separate",
    "hydrate full assay context only after selection",
)
DEFAULT_VARIANT_PLANNING_KEYS = (
    "protein_ref",
    "parent_protein_ref",
    "variant_signature",
    "variant_kind",
    "sequence_delta_signature",
    "construct_type",
)
DEFAULT_VARIANT_DEFERRED_PAYLOADS = (
    "full_variant_annotation_rows",
    "mutation_projection_payload",
    "construct_metadata",
)
DEFAULT_VARIANT_LAZY_GUIDANCE = (
    "keep parent protein lineage visible alongside the variant signature",
    "defer full mutation and construct payloads until selection",
)
DEFAULT_STRUCTURE_UNIT_PLANNING_KEYS = (
    "protein_ref",
    "variant_ref",
    "structure_source",
    "structure_id",
    "chain_id",
    "entity_id",
    "assembly_id",
    "mapping_status",
)
DEFAULT_STRUCTURE_UNIT_DEFERRED_PAYLOADS = (
    "full_structure_mapping_payload",
    "coordinate_projection_payload",
    "confidence_or_resolution_context",
)
DEFAULT_STRUCTURE_UNIT_LAZY_GUIDANCE = (
    "keep experimental and predicted structures separate",
    "defer coordinate-heavy structure projections until selection",
)


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


def _normalize_int(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer or None")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be an integer or None") from exc


def _normalize_float(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric or None")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be numeric or None") from exc


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


def _normalize_storage_tier(value: Any) -> SummaryStorageTier:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    aliases: dict[str, SummaryStorageTier] = {
        "planning_index": "planning_index",
        "canonical_store": "canonical_store",
        "feature_cache": "feature_cache",
        "deferred_fetch": "deferred_fetch",
        "lazy": "deferred_fetch",
        "scrape_only": "scrape_only",
    }
    tier = aliases.get(text)
    if tier is None:
        raise ValueError(f"unsupported storage_tier: {value!r}")
    return tier


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _coerce_materialization_pointers(
    values: Any,
) -> tuple[PlanningIndexMaterializationPointer, ...]:
    pointers: list[PlanningIndexMaterializationPointer] = []
    for value in _iter_values(values):
        if isinstance(value, PlanningIndexMaterializationPointer):
            pointers.append(value)
        elif isinstance(value, Mapping):
            pointers.append(PlanningIndexMaterializationPointer.from_dict(value))
        else:
            raise TypeError(
                "materialization_pointers must contain PlanningIndexMaterializationPointer "
                "objects or mappings"
            )
    return tuple(pointers)


def _coerce_source_connections(
    values: Any,
) -> tuple[SummarySourceConnection, ...]:
    connections: list[SummarySourceConnection] = []
    for value in _iter_values(values):
        if isinstance(value, SummarySourceConnection):
            connections.append(value)
        elif isinstance(value, Mapping):
            connections.append(SummarySourceConnection.from_dict(value))
        else:
            raise TypeError(
                "source_connections must contain SummarySourceConnection objects or mappings"
            )
    return tuple(connections)


@dataclass(frozen=True, slots=True)
class SummaryReference:
    reference_kind: SummaryReferenceKind
    namespace: str
    identifier: str
    label: str = ""
    join_status: JoinStatus = "candidate"
    source_name: str | None = None
    source_record_id: str | None = None
    span_start: int | None = None
    span_end: int | None = None
    evidence_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_kind", _clean_text(self.reference_kind))
        object.__setattr__(self, "namespace", _clean_text(self.namespace))
        object.__setattr__(self, "identifier", _clean_text(self.identifier))
        object.__setattr__(self, "label", _clean_text(self.label))
        object.__setattr__(self, "join_status", _normalize_join_status(self.join_status))
        object.__setattr__(self, "source_name", _optional_text(self.source_name))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(self, "span_start", _normalize_int(self.span_start, "span_start"))
        object.__setattr__(self, "span_end", _normalize_int(self.span_end, "span_end"))
        object.__setattr__(self, "evidence_refs", _clean_text_tuple(self.evidence_refs))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.reference_kind:
            raise ValueError("reference_kind must not be empty")
        if not self.namespace:
            raise ValueError("namespace must not be empty")
        if not self.identifier:
            raise ValueError("identifier must not be empty")
        if self.span_start is not None and self.span_end is not None:
            if self.span_start > self.span_end:
                raise ValueError("span_start must be <= span_end")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_kind": self.reference_kind,
            "namespace": self.namespace,
            "identifier": self.identifier,
            "label": self.label,
            "join_status": self.join_status,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "evidence_refs": list(self.evidence_refs),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SummaryReference:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            reference_kind=payload.get("reference_kind")
            or payload.get("kind")
            or "cross_reference",
            namespace=payload.get("namespace") or payload.get("source_namespace") or "",
            identifier=payload.get("identifier") or payload.get("id") or "",
            label=payload.get("label") or payload.get("name") or "",
            join_status=payload.get("join_status") or payload.get("status") or "candidate",
            source_name=payload.get("source_name") or payload.get("source"),
            source_record_id=payload.get("source_record_id") or payload.get("record_id"),
            span_start=payload.get("span_start") or payload.get("start"),
            span_end=payload.get("span_end") or payload.get("end"),
            evidence_refs=payload.get("evidence_refs") or payload.get("provenance_refs") or (),
            notes=payload.get("notes") or payload.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class SummaryBiologicalOrigin:
    organism_name: str
    taxon_id: int | None = None
    lineage: tuple[str, ...] = ()
    strain: str | None = None
    tissue: str | None = None
    cell_type: str | None = None
    cell_line: str | None = None
    compartment: str | None = None
    developmental_stage: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "organism_name", _clean_text(self.organism_name))
        object.__setattr__(self, "taxon_id", _normalize_int(self.taxon_id, "taxon_id"))
        object.__setattr__(self, "lineage", _clean_text_tuple(self.lineage))
        object.__setattr__(self, "strain", _optional_text(self.strain))
        object.__setattr__(self, "tissue", _optional_text(self.tissue))
        object.__setattr__(self, "cell_type", _optional_text(self.cell_type))
        object.__setattr__(self, "cell_line", _optional_text(self.cell_line))
        object.__setattr__(self, "compartment", _optional_text(self.compartment))
        object.__setattr__(
            self,
            "developmental_stage",
            _optional_text(self.developmental_stage),
        )
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.organism_name:
            raise ValueError("organism_name must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "organism_name": self.organism_name,
            "taxon_id": self.taxon_id,
            "lineage": list(self.lineage),
            "strain": self.strain,
            "tissue": self.tissue,
            "cell_type": self.cell_type,
            "cell_line": self.cell_line,
            "compartment": self.compartment,
            "developmental_stage": self.developmental_stage,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SummaryBiologicalOrigin:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            organism_name=payload.get("organism_name") or payload.get("organism") or "",
            taxon_id=payload.get("taxon_id") or payload.get("tax_id"),
            lineage=payload.get("lineage") or payload.get("taxonomy") or (),
            strain=payload.get("strain"),
            tissue=payload.get("tissue"),
            cell_type=payload.get("cell_type"),
            cell_line=payload.get("cell_line"),
            compartment=payload.get("compartment"),
            developmental_stage=payload.get("developmental_stage"),
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class SummaryProvenancePointer:
    provenance_id: str
    source_name: str
    source_record_id: str | None = None
    release_version: str | None = None
    release_date: str | None = None
    acquired_at: str | None = None
    checksum: str | None = None
    join_status: JoinStatus = "joined"
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance_id", _clean_text(self.provenance_id))
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(self, "release_version", _optional_text(self.release_version))
        object.__setattr__(self, "release_date", _optional_text(self.release_date))
        object.__setattr__(self, "acquired_at", _optional_text(self.acquired_at))
        object.__setattr__(self, "checksum", _optional_text(self.checksum))
        object.__setattr__(self, "join_status", _normalize_join_status(self.join_status))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.provenance_id:
            raise ValueError("provenance_id must not be empty")
        if not self.source_name:
            raise ValueError("source_name must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance_id": self.provenance_id,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "release_version": self.release_version,
            "release_date": self.release_date,
            "acquired_at": self.acquired_at,
            "checksum": self.checksum,
            "join_status": self.join_status,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SummaryProvenancePointer:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            provenance_id=payload.get("provenance_id") or payload.get("id") or "",
            source_name=payload.get("source_name") or payload.get("source") or "",
            source_record_id=payload.get("source_record_id") or payload.get("record_id"),
            release_version=payload.get("release_version") or payload.get("version"),
            release_date=payload.get("release_date") or payload.get("date"),
            acquired_at=payload.get("acquired_at") or payload.get("timestamp"),
            checksum=payload.get("checksum"),
            join_status=payload.get("join_status") or payload.get("status") or "joined",
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class SummarySourceClaim:
    source_name: str
    value: Any = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        if not self.source_name:
            raise ValueError("source_name must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "value": _json_ready(self.value),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SummarySourceClaim:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_name=payload.get("source_name") or payload.get("source") or "",
            value=payload.get("value"),
        )


@dataclass(frozen=True, slots=True)
class SummarySourceRollup:
    field_name: str
    claim_class: str
    source_precedence: tuple[str, ...] = ()
    source_values: tuple[SummarySourceClaim, ...] = ()
    winner_source: str | None = None
    winner_value: Any = None
    corroborating_sources: tuple[str, ...] = ()
    disagreeing_sources: tuple[str, ...] = ()
    status: str = "partial"
    partial: bool = True
    partial_reason: str = ""
    trust_policy: str = "p29_source_trust_policy"

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_name", _clean_text(self.field_name))
        object.__setattr__(self, "claim_class", _clean_text(self.claim_class))
        object.__setattr__(self, "source_precedence", _clean_text_tuple(self.source_precedence))
        object.__setattr__(
            self,
            "source_values",
            tuple(
                value
                if isinstance(value, SummarySourceClaim)
                else SummarySourceClaim.from_dict(value)
                for value in _iter_values(self.source_values)
            ),
        )
        object.__setattr__(self, "winner_source", _optional_text(self.winner_source))
        object.__setattr__(
            self,
            "corroborating_sources",
            _clean_text_tuple(self.corroborating_sources),
        )
        object.__setattr__(self, "disagreeing_sources", _clean_text_tuple(self.disagreeing_sources))
        object.__setattr__(self, "status", _clean_text(self.status) or "partial")
        object.__setattr__(self, "partial", bool(self.partial))
        object.__setattr__(self, "partial_reason", _clean_text(self.partial_reason))
        object.__setattr__(self, "trust_policy", _clean_text(self.trust_policy))
        if not self.field_name:
            raise ValueError("field_name must not be empty")
        if not self.claim_class:
            raise ValueError("claim_class must not be empty")
        if not self.trust_policy:
            raise ValueError("trust_policy must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "claim_class": self.claim_class,
            "source_precedence": list(self.source_precedence),
            "source_values": [value.to_dict() for value in self.source_values],
            "winner_source": self.winner_source,
            "winner_value": _json_ready(self.winner_value),
            "corroborating_sources": list(self.corroborating_sources),
            "disagreeing_sources": list(self.disagreeing_sources),
            "status": self.status,
            "partial": self.partial,
            "partial_reason": self.partial_reason,
            "trust_policy": self.trust_policy,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SummarySourceRollup:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            field_name=payload.get("field_name") or payload.get("field") or "",
            claim_class=payload.get("claim_class") or payload.get("class") or "",
            source_precedence=payload.get("source_precedence") or payload.get("precedence") or (),
            source_values=tuple(
                SummarySourceClaim.from_dict(item)
                for item in _iter_values(
                    payload.get("source_values") or payload.get("values") or ()
                )
            ),
            winner_source=payload.get("winner_source") or payload.get("winner"),
            winner_value=payload.get("winner_value"),
            corroborating_sources=payload.get("corroborating_sources")
            or payload.get("supporting_sources")
            or (),
            disagreeing_sources=payload.get("disagreeing_sources") or (),
            status=payload.get("status") or "partial",
            partial=(
                payload.get("partial")
                if payload.get("partial") is not None
                else payload.get("status") == "partial"
            ),
            partial_reason=payload.get("partial_reason") or "",
            trust_policy=payload.get("trust_policy") or "p29_source_trust_policy",
        )


@dataclass(frozen=True, slots=True)
class SummarySourceConnection:
    connection_kind: str
    source_names: tuple[str, ...] = ()
    direct_sources: tuple[str, ...] = ()
    indirect_sources: tuple[str, ...] = ()
    bridge_ids: tuple[str, ...] = ()
    bridge_source: str | None = None
    join_mode: str = "direct"
    join_status: JoinStatus = "candidate"
    trust_policy: str = "p29_source_trust_policy"
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "connection_kind", _clean_text(self.connection_kind))
        object.__setattr__(self, "source_names", _clean_text_tuple(self.source_names))
        object.__setattr__(self, "direct_sources", _clean_text_tuple(self.direct_sources))
        object.__setattr__(self, "indirect_sources", _clean_text_tuple(self.indirect_sources))
        object.__setattr__(self, "bridge_ids", _clean_text_tuple(self.bridge_ids))
        object.__setattr__(self, "bridge_source", _optional_text(self.bridge_source))
        object.__setattr__(self, "join_mode", _clean_text(self.join_mode) or "direct")
        object.__setattr__(self, "join_status", _normalize_join_status(self.join_status))
        object.__setattr__(self, "trust_policy", _clean_text(self.trust_policy))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.connection_kind:
            raise ValueError("connection_kind must not be empty")
        if not self.trust_policy:
            raise ValueError("trust_policy must not be empty")
        if self.join_mode not in {"direct", "indirect", "partial"}:
            raise ValueError("join_mode must be direct, indirect, or partial")

    def to_dict(self) -> dict[str, Any]:
        return {
            "connection_kind": self.connection_kind,
            "source_names": list(self.source_names),
            "direct_sources": list(self.direct_sources),
            "indirect_sources": list(self.indirect_sources),
            "bridge_ids": list(self.bridge_ids),
            "bridge_source": self.bridge_source,
            "join_mode": self.join_mode,
            "join_status": self.join_status,
            "trust_policy": self.trust_policy,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SummarySourceConnection:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            connection_kind=payload.get("connection_kind")
            or payload.get("kind")
            or payload.get("bridge_kind")
            or "",
            source_names=payload.get("source_names") or payload.get("sources") or (),
            direct_sources=payload.get("direct_sources") or (),
            indirect_sources=payload.get("indirect_sources") or (),
            bridge_ids=payload.get("bridge_ids") or payload.get("bridge_keys") or (),
            bridge_source=payload.get("bridge_source"),
            join_mode=payload.get("join_mode") or "direct",
            join_status=payload.get("join_status") or payload.get("status") or "candidate",
            trust_policy=payload.get("trust_policy") or "p29_source_trust_policy",
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class SummaryCrossSourceView:
    direct_joins: tuple[SummarySourceConnection, ...] = ()
    indirect_bridges: tuple[SummarySourceConnection, ...] = ()
    partial_joins: tuple[SummarySourceConnection, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "direct_joins",
            _coerce_source_connections(self.direct_joins),
        )
        object.__setattr__(
            self,
            "indirect_bridges",
            _coerce_source_connections(self.indirect_bridges),
        )
        object.__setattr__(
            self,
            "partial_joins",
            _coerce_source_connections(self.partial_joins),
        )

    @classmethod
    def from_connections(
        cls,
        connections: Iterable[SummarySourceConnection],
    ) -> SummaryCrossSourceView:
        direct_joins: list[SummarySourceConnection] = []
        indirect_bridges: list[SummarySourceConnection] = []
        partial_joins: list[SummarySourceConnection] = []
        for connection in connections:
            if not isinstance(connection, SummarySourceConnection):
                connection = SummarySourceConnection.from_dict(connection)
            if connection.join_mode == "direct":
                direct_joins.append(connection)
            elif connection.join_mode == "indirect":
                indirect_bridges.append(connection)
            elif connection.join_mode == "partial":
                partial_joins.append(connection)
        return cls(
            direct_joins=tuple(direct_joins),
            indirect_bridges=tuple(indirect_bridges),
            partial_joins=tuple(partial_joins),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "direct_joins": [connection.to_dict() for connection in self.direct_joins],
            "indirect_bridges": [
                connection.to_dict() for connection in self.indirect_bridges
            ],
            "partial_joins": [connection.to_dict() for connection in self.partial_joins],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SummaryCrossSourceView:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            direct_joins=payload.get("direct_joins") or payload.get("direct") or (),
            indirect_bridges=payload.get("indirect_bridges")
            or payload.get("indirect")
            or (),
            partial_joins=payload.get("partial_joins") or payload.get("partial") or (),
        )


@dataclass(frozen=True, slots=True)
class SummaryRecordContext:
    provenance_pointers: tuple[SummaryProvenancePointer, ...] = ()
    cross_references: tuple[SummaryReference, ...] = ()
    motif_references: tuple[SummaryReference, ...] = ()
    domain_references: tuple[SummaryReference, ...] = ()
    pathway_references: tuple[SummaryReference, ...] = ()
    source_rollups: tuple[SummarySourceRollup, ...] = ()
    source_connections: tuple[SummarySourceConnection, ...] = ()
    biological_origin: SummaryBiologicalOrigin | None = None
    materialization_pointers: tuple[PlanningIndexMaterializationPointer, ...] = ()
    planning_index_keys: tuple[str, ...] = ()
    deferred_payloads: tuple[str, ...] = ()
    lazy_loading_guidance: tuple[str, ...] = ()
    storage_notes: tuple[str, ...] = ()
    storage_tier: SummaryStorageTier = "feature_cache"
    cross_source_view: SummaryCrossSourceView | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provenance_pointers",
            tuple(
                pointer
                if isinstance(pointer, SummaryProvenancePointer)
                else SummaryProvenancePointer.from_dict(pointer)
                for pointer in _iter_values(self.provenance_pointers)
            ),
        )
        object.__setattr__(
            self,
            "cross_references",
            tuple(
                reference
                if isinstance(reference, SummaryReference)
                else SummaryReference.from_dict(reference)
                for reference in _iter_values(self.cross_references)
            ),
        )
        object.__setattr__(
            self,
            "motif_references",
            tuple(
                reference
                if isinstance(reference, SummaryReference)
                else SummaryReference.from_dict(reference)
                for reference in _iter_values(self.motif_references)
            ),
        )
        object.__setattr__(
            self,
            "domain_references",
            tuple(
                reference
                if isinstance(reference, SummaryReference)
                else SummaryReference.from_dict(reference)
                for reference in _iter_values(self.domain_references)
            ),
        )
        object.__setattr__(
            self,
            "pathway_references",
            tuple(
                reference
                if isinstance(reference, SummaryReference)
                else SummaryReference.from_dict(reference)
                for reference in _iter_values(self.pathway_references)
            ),
        )
        object.__setattr__(
            self,
            "source_rollups",
            tuple(
                rollup
                if isinstance(rollup, SummarySourceRollup)
                else SummarySourceRollup.from_dict(rollup)
                for rollup in _iter_values(self.source_rollups)
            ),
        )
        object.__setattr__(
            self,
            "source_connections",
            tuple(
                connection
                if isinstance(connection, SummarySourceConnection)
                else SummarySourceConnection.from_dict(connection)
                for connection in _iter_values(self.source_connections)
            ),
        )
        if self.biological_origin is not None and not isinstance(
            self.biological_origin,
            SummaryBiologicalOrigin,
        ):
            object.__setattr__(
                self,
                "biological_origin",
                SummaryBiologicalOrigin.from_dict(self.biological_origin),
            )
        object.__setattr__(
            self,
            "materialization_pointers",
            _coerce_materialization_pointers(self.materialization_pointers),
        )
        object.__setattr__(self, "planning_index_keys", _clean_text_tuple(self.planning_index_keys))
        object.__setattr__(self, "deferred_payloads", _clean_text_tuple(self.deferred_payloads))
        object.__setattr__(
            self,
            "lazy_loading_guidance",
            _clean_text_tuple(self.lazy_loading_guidance),
        )
        object.__setattr__(self, "storage_notes", _clean_text_tuple(self.storage_notes))
        object.__setattr__(self, "storage_tier", _normalize_storage_tier(self.storage_tier))
        if self.cross_source_view is not None and not isinstance(
            self.cross_source_view,
            SummaryCrossSourceView,
        ):
            object.__setattr__(
                self,
                "cross_source_view",
                SummaryCrossSourceView.from_dict(self.cross_source_view),
            )

    @property
    def all_references(self) -> tuple[SummaryReference, ...]:
        return (
            *self.cross_references,
            *self.motif_references,
            *self.domain_references,
            *self.pathway_references,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance_pointers": [pointer.to_dict() for pointer in self.provenance_pointers],
            "cross_references": [reference.to_dict() for reference in self.cross_references],
            "motif_references": [reference.to_dict() for reference in self.motif_references],
            "domain_references": [reference.to_dict() for reference in self.domain_references],
            "pathway_references": [reference.to_dict() for reference in self.pathway_references],
            "source_rollups": [rollup.to_dict() for rollup in self.source_rollups],
            "source_connections": [
                connection.to_dict() for connection in self.source_connections
            ],
            "cross_source_view": (
                self.cross_source_view.to_dict() if self.cross_source_view is not None else None
            ),
            "biological_origin": (
                self.biological_origin.to_dict() if self.biological_origin is not None else None
            ),
            "materialization_pointers": [
                pointer.to_dict() for pointer in self.materialization_pointers
            ],
            "planning_index_keys": list(self.planning_index_keys),
            "deferred_payloads": list(self.deferred_payloads),
            "lazy_loading_guidance": list(self.lazy_loading_guidance),
            "storage_notes": list(self.storage_notes),
            "storage_tier": self.storage_tier,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SummaryRecordContext:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            provenance_pointers=tuple(
                SummaryProvenancePointer.from_dict(item)
                for item in _iter_values(
                    payload.get("provenance_pointers") or payload.get("provenance") or ()
                )
            ),
            cross_references=tuple(
                SummaryReference.from_dict(item)
                for item in _iter_values(
                    payload.get("cross_references") or payload.get("cross_refs") or ()
                )
            ),
            motif_references=tuple(
                SummaryReference.from_dict(item)
                for item in _iter_values(
                    payload.get("motif_references") or payload.get("motifs") or ()
                )
            ),
            domain_references=tuple(
                SummaryReference.from_dict(item)
                for item in _iter_values(
                    payload.get("domain_references") or payload.get("domains") or ()
                )
            ),
            pathway_references=tuple(
                SummaryReference.from_dict(item)
                for item in _iter_values(
                    payload.get("pathway_references") or payload.get("pathways") or ()
                )
            ),
            source_rollups=tuple(
                SummarySourceRollup.from_dict(item)
                for item in _iter_values(
                    payload.get("source_rollups") or payload.get("rollups") or ()
                )
            ),
            source_connections=tuple(
                SummarySourceConnection.from_dict(item)
                for item in _iter_values(
                    payload.get("source_connections")
                    or payload.get("connections")
                    or ()
                )
            ),
            cross_source_view=payload.get("cross_source_view")
            or payload.get("connection_view")
            or payload.get("cross_source_connection_view"),
            biological_origin=payload.get("biological_origin") or payload.get("origin"),
            materialization_pointers=tuple(
                payload.get("materialization_pointers")
                or payload.get("deferred_materialization_pointers")
                or ()
            ),
            planning_index_keys=payload.get("planning_index_keys")
            or payload.get("index_keys")
            or (),
            deferred_payloads=payload.get("deferred_payloads") or payload.get("deferred") or (),
            lazy_loading_guidance=payload.get("lazy_loading_guidance")
            or payload.get("lazy_guidance")
            or (),
            storage_notes=payload.get("storage_notes") or payload.get("notes") or (),
            storage_tier=payload.get("storage_tier") or "feature_cache",
        )


def _with_defaults(
    context: SummaryRecordContext,
    *,
    storage_tier: SummaryStorageTier,
    planning_index_keys: tuple[str, ...],
    deferred_payloads: tuple[str, ...],
    lazy_loading_guidance: tuple[str, ...],
    storage_notes: tuple[str, ...],
) -> SummaryRecordContext:
    return replace(
        context,
        storage_tier=context.storage_tier if context.storage_tier else storage_tier,
        planning_index_keys=context.planning_index_keys or planning_index_keys,
        deferred_payloads=context.deferred_payloads or deferred_payloads,
        lazy_loading_guidance=context.lazy_loading_guidance or lazy_loading_guidance,
        storage_notes=context.storage_notes or storage_notes,
    )


@dataclass(frozen=True, slots=True)
class ProteinSummaryRecord:
    summary_id: str
    protein_ref: str
    protein_name: str = ""
    organism_name: str = ""
    taxon_id: int | None = None
    sequence_checksum: str | None = None
    sequence_version: str | None = None
    sequence_length: int | None = None
    gene_names: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    join_status: JoinStatus = "joined"
    join_reason: str = ""
    context: SummaryRecordContext = field(default_factory=SummaryRecordContext)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary_id", _clean_text(self.summary_id))
        object.__setattr__(self, "protein_ref", _clean_text(self.protein_ref))
        object.__setattr__(self, "protein_name", _clean_text(self.protein_name))
        object.__setattr__(self, "organism_name", _clean_text(self.organism_name))
        object.__setattr__(self, "taxon_id", _normalize_int(self.taxon_id, "taxon_id"))
        object.__setattr__(self, "sequence_checksum", _optional_text(self.sequence_checksum))
        object.__setattr__(self, "sequence_version", _optional_text(self.sequence_version))
        object.__setattr__(
            self,
            "sequence_length",
            _normalize_int(self.sequence_length, "sequence_length"),
        )
        object.__setattr__(self, "gene_names", _clean_text_tuple(self.gene_names))
        object.__setattr__(self, "aliases", _clean_text_tuple(self.aliases))
        object.__setattr__(self, "join_status", _normalize_join_status(self.join_status))
        object.__setattr__(self, "join_reason", _clean_text(self.join_reason))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.summary_id:
            raise ValueError("summary_id must not be empty")
        if not self.protein_ref:
            raise ValueError("protein_ref must not be empty")
        context = (
            self.context
            if isinstance(self.context, SummaryRecordContext)
            else SummaryRecordContext.from_dict(self.context)
        )
        object.__setattr__(
            self,
            "context",
            _with_defaults(
                context,
                storage_tier="feature_cache",
                planning_index_keys=DEFAULT_PROTEIN_PLANNING_KEYS,
                deferred_payloads=DEFAULT_PROTEIN_DEFERRED_PAYLOADS,
                lazy_loading_guidance=DEFAULT_PROTEIN_LAZY_GUIDANCE,
                storage_notes=(
                    "pin release-stamped protein snapshots before materialization",
                    "keep secondary accessions as aliases rather than alternate primaries",
                ),
            ),
        )

    @property
    def record_type(self) -> SummaryRecordKind:
        return "protein"

    @property
    def canonical_id(self) -> str:
        return self.protein_ref

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "summary_id": self.summary_id,
            "protein_ref": self.protein_ref,
            "protein_name": self.protein_name,
            "organism_name": self.organism_name,
            "taxon_id": self.taxon_id,
            "sequence_checksum": self.sequence_checksum,
            "sequence_version": self.sequence_version,
            "sequence_length": self.sequence_length,
            "gene_names": list(self.gene_names),
            "aliases": list(self.aliases),
            "join_status": self.join_status,
            "join_reason": self.join_reason,
            "context": self.context.to_dict(),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProteinSummaryRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            summary_id=payload.get("summary_id") or payload.get("id") or "",
            protein_ref=payload.get("protein_ref")
            or payload.get("canonical_protein_id")
            or payload.get("canonical_id")
            or payload.get("accession")
            or "",
            protein_name=payload.get("protein_name") or payload.get("name") or "",
            organism_name=payload.get("organism_name") or payload.get("organism") or "",
            taxon_id=payload.get("taxon_id") or payload.get("tax_id"),
            sequence_checksum=payload.get("sequence_checksum") or payload.get("checksum"),
            sequence_version=payload.get("sequence_version") or payload.get("version"),
            sequence_length=payload.get("sequence_length"),
            gene_names=payload.get("gene_names") or payload.get("genes") or (),
            aliases=payload.get("aliases") or payload.get("secondary_accessions") or (),
            join_status=payload.get("join_status") or payload.get("status") or "joined",
            join_reason=payload.get("join_reason") or payload.get("reason") or "",
            context=SummaryRecordContext.from_dict(payload.get("context") or {}),
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class ProteinProteinSummaryRecord:
    summary_id: str
    protein_a_ref: str
    protein_b_ref: str
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
    join_status: JoinStatus = "joined"
    join_reason: str = ""
    context: SummaryRecordContext = field(default_factory=SummaryRecordContext)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary_id", _clean_text(self.summary_id))
        object.__setattr__(self, "protein_a_ref", _clean_text(self.protein_a_ref))
        object.__setattr__(self, "protein_b_ref", _clean_text(self.protein_b_ref))
        object.__setattr__(self, "interaction_type", _clean_text(self.interaction_type))
        object.__setattr__(self, "interaction_id", _optional_text(self.interaction_id))
        object.__setattr__(self, "interaction_refs", _clean_text_tuple(self.interaction_refs))
        object.__setattr__(self, "evidence_refs", _clean_text_tuple(self.evidence_refs))
        object.__setattr__(self, "organism_name", _clean_text(self.organism_name))
        object.__setattr__(self, "taxon_id", _normalize_int(self.taxon_id, "taxon_id"))
        object.__setattr__(self, "physical_interaction", self.physical_interaction)
        object.__setattr__(self, "directionality", _optional_text(self.directionality))
        object.__setattr__(
            self,
            "evidence_count",
            _normalize_int(self.evidence_count, "evidence_count"),
        )
        object.__setattr__(self, "confidence", _normalize_float(self.confidence, "confidence"))
        object.__setattr__(self, "join_status", _normalize_join_status(self.join_status))
        object.__setattr__(self, "join_reason", _clean_text(self.join_reason))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.summary_id:
            raise ValueError("summary_id must not be empty")
        if not self.protein_a_ref:
            raise ValueError("protein_a_ref must not be empty")
        if not self.protein_b_ref:
            raise ValueError("protein_b_ref must not be empty")
        if self.protein_a_ref == self.protein_b_ref:
            raise ValueError("protein_a_ref and protein_b_ref must be different")
        context = (
            self.context
            if isinstance(self.context, SummaryRecordContext)
            else SummaryRecordContext.from_dict(self.context)
        )
        object.__setattr__(
            self,
            "context",
            _with_defaults(
                context,
                storage_tier="feature_cache",
                planning_index_keys=DEFAULT_PAIR_PLANNING_KEYS,
                deferred_payloads=DEFAULT_PAIR_DEFERRED_PAYLOADS,
                lazy_loading_guidance=DEFAULT_PAIR_LAZY_GUIDANCE,
                storage_notes=(
                    "preserve native interaction identifiers and projection lineage",
                    "do not flatten n-ary complexes into binary summaries without traceability",
                ),
            ),
        )

    @property
    def record_type(self) -> SummaryRecordKind:
        return "protein_protein"

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "summary_id": self.summary_id,
            "protein_a_ref": self.protein_a_ref,
            "protein_b_ref": self.protein_b_ref,
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
            "context": self.context.to_dict(),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProteinProteinSummaryRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            summary_id=payload.get("summary_id") or payload.get("id") or "",
            protein_a_ref=payload.get("protein_a_ref") or payload.get("left_ref") or "",
            protein_b_ref=payload.get("protein_b_ref") or payload.get("right_ref") or "",
            interaction_type=payload.get("interaction_type") or payload.get("kind") or "",
            interaction_id=payload.get("interaction_id") or payload.get("pair_id"),
            interaction_refs=payload.get("interaction_refs")
            or payload.get("interaction_ids")
            or (),
            evidence_refs=payload.get("evidence_refs") or payload.get("provenance_refs") or (),
            organism_name=payload.get("organism_name") or payload.get("organism") or "",
            taxon_id=payload.get("taxon_id") or payload.get("tax_id"),
            physical_interaction=payload.get("physical_interaction"),
            directionality=payload.get("directionality"),
            evidence_count=payload.get("evidence_count"),
            confidence=payload.get("confidence"),
            join_status=payload.get("join_status") or payload.get("status") or "joined",
            join_reason=payload.get("join_reason") or payload.get("reason") or "",
            context=SummaryRecordContext.from_dict(payload.get("context") or {}),
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class ProteinVariantSummaryRecord:
    summary_id: str
    protein_ref: str
    parent_protein_ref: str | None = None
    variant_signature: str = ""
    variant_kind: str = ""
    mutation_list: tuple[str, ...] = ()
    sequence_delta_signature: str | None = None
    construct_type: str | None = None
    is_partial: bool | None = None
    organism_name: str = ""
    taxon_id: int | None = None
    variant_relation_notes: tuple[str, ...] = ()
    join_status: JoinStatus = "joined"
    join_reason: str = ""
    context: SummaryRecordContext = field(default_factory=SummaryRecordContext)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary_id", _clean_text(self.summary_id))
        object.__setattr__(self, "protein_ref", _clean_text(self.protein_ref))
        object.__setattr__(
            self,
            "parent_protein_ref",
            _optional_text(self.parent_protein_ref) or self.protein_ref,
        )
        object.__setattr__(self, "variant_signature", _clean_text(self.variant_signature))
        object.__setattr__(self, "variant_kind", _clean_text(self.variant_kind))
        object.__setattr__(self, "mutation_list", _clean_text_tuple(self.mutation_list))
        object.__setattr__(
            self,
            "sequence_delta_signature",
            _optional_text(self.sequence_delta_signature),
        )
        object.__setattr__(self, "construct_type", _optional_text(self.construct_type))
        object.__setattr__(self, "is_partial", self.is_partial)
        object.__setattr__(self, "organism_name", _clean_text(self.organism_name))
        object.__setattr__(self, "taxon_id", _normalize_int(self.taxon_id, "taxon_id"))
        object.__setattr__(
            self,
            "variant_relation_notes",
            _clean_text_tuple(self.variant_relation_notes),
        )
        object.__setattr__(self, "join_status", _normalize_join_status(self.join_status))
        object.__setattr__(self, "join_reason", _clean_text(self.join_reason))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.summary_id:
            raise ValueError("summary_id must not be empty")
        if not self.protein_ref:
            raise ValueError("protein_ref must not be empty")
        if not self.variant_signature:
            raise ValueError("variant_signature must not be empty")
        context = (
            self.context
            if isinstance(self.context, SummaryRecordContext)
            else SummaryRecordContext.from_dict(self.context)
        )
        object.__setattr__(
            self,
            "context",
            _with_defaults(
                context,
                storage_tier="feature_cache",
                planning_index_keys=DEFAULT_VARIANT_PLANNING_KEYS,
                deferred_payloads=DEFAULT_VARIANT_DEFERRED_PAYLOADS,
                lazy_loading_guidance=DEFAULT_VARIANT_LAZY_GUIDANCE,
                storage_notes=(
                    "preserve parent protein lineage and variant signature together",
                    "do not collapse engineered, isoform, and wild-type constructs into one row",
                ),
            ),
        )

    @property
    def record_type(self) -> SummaryRecordKind:
        return "protein_variant"

    @property
    def canonical_id(self) -> str:
        return f"{self.protein_ref}:{self.variant_signature}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "summary_id": self.summary_id,
            "protein_ref": self.protein_ref,
            "parent_protein_ref": self.parent_protein_ref,
            "variant_signature": self.variant_signature,
            "variant_kind": self.variant_kind,
            "mutation_list": list(self.mutation_list),
            "sequence_delta_signature": self.sequence_delta_signature,
            "construct_type": self.construct_type,
            "is_partial": self.is_partial,
            "organism_name": self.organism_name,
            "taxon_id": self.taxon_id,
            "variant_relation_notes": list(self.variant_relation_notes),
            "join_status": self.join_status,
            "join_reason": self.join_reason,
            "context": self.context.to_dict(),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProteinVariantSummaryRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            summary_id=payload.get("summary_id") or payload.get("id") or "",
            protein_ref=payload.get("protein_ref") or payload.get("accession") or "",
            parent_protein_ref=payload.get("parent_protein_ref")
            or payload.get("parent_ref"),
            variant_signature=payload.get("variant_signature")
            or payload.get("signature")
            or "",
            variant_kind=payload.get("variant_kind") or payload.get("kind") or "",
            mutation_list=payload.get("mutation_list")
            or payload.get("mutations")
            or (),
            sequence_delta_signature=payload.get("sequence_delta_signature")
            or payload.get("delta_signature"),
            construct_type=payload.get("construct_type"),
            is_partial=payload.get("is_partial"),
            organism_name=payload.get("organism_name") or payload.get("organism") or "",
            taxon_id=payload.get("taxon_id") or payload.get("tax_id"),
            variant_relation_notes=payload.get("variant_relation_notes")
            or payload.get("relation_notes")
            or (),
            join_status=payload.get("join_status") or payload.get("status") or "joined",
            join_reason=payload.get("join_reason") or payload.get("reason") or "",
            context=SummaryRecordContext.from_dict(payload.get("context") or {}),
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class StructureUnitSummaryRecord:
    summary_id: str
    protein_ref: str
    structure_source: str
    structure_id: str
    variant_ref: str | None = None
    structure_kind: str = ""
    model_id: str | None = None
    entity_id: str | None = None
    chain_id: str | None = None
    assembly_id: str | None = None
    residue_span_start: int | None = None
    residue_span_end: int | None = None
    resolution_or_confidence: float | None = None
    experimental_or_predicted: str = ""
    mapping_status: JoinStatus = "joined"
    structure_relation_notes: tuple[str, ...] = ()
    join_status: JoinStatus = "joined"
    join_reason: str = ""
    context: SummaryRecordContext = field(default_factory=SummaryRecordContext)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary_id", _clean_text(self.summary_id))
        object.__setattr__(self, "protein_ref", _clean_text(self.protein_ref))
        object.__setattr__(self, "structure_source", _clean_text(self.structure_source))
        object.__setattr__(self, "structure_id", _clean_text(self.structure_id))
        object.__setattr__(self, "variant_ref", _optional_text(self.variant_ref))
        object.__setattr__(self, "structure_kind", _clean_text(self.structure_kind))
        object.__setattr__(self, "model_id", _optional_text(self.model_id))
        object.__setattr__(self, "entity_id", _optional_text(self.entity_id))
        object.__setattr__(self, "chain_id", _optional_text(self.chain_id))
        object.__setattr__(self, "assembly_id", _optional_text(self.assembly_id))
        object.__setattr__(
            self,
            "residue_span_start",
            _normalize_int(self.residue_span_start, "residue_span_start"),
        )
        object.__setattr__(
            self,
            "residue_span_end",
            _normalize_int(self.residue_span_end, "residue_span_end"),
        )
        object.__setattr__(
            self,
            "resolution_or_confidence",
            _normalize_float(self.resolution_or_confidence, "resolution_or_confidence"),
        )
        object.__setattr__(
            self,
            "experimental_or_predicted",
            _clean_text(self.experimental_or_predicted),
        )
        object.__setattr__(
            self,
            "mapping_status",
            _normalize_join_status(self.mapping_status),
        )
        object.__setattr__(
            self,
            "structure_relation_notes",
            _clean_text_tuple(self.structure_relation_notes),
        )
        object.__setattr__(self, "join_status", _normalize_join_status(self.join_status))
        object.__setattr__(self, "join_reason", _clean_text(self.join_reason))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.summary_id:
            raise ValueError("summary_id must not be empty")
        if not self.protein_ref:
            raise ValueError("protein_ref must not be empty")
        if not self.structure_source:
            raise ValueError("structure_source must not be empty")
        if not self.structure_id:
            raise ValueError("structure_id must not be empty")
        if (
            self.residue_span_start is not None
            and self.residue_span_end is not None
            and self.residue_span_start > self.residue_span_end
        ):
            raise ValueError("residue_span_start must be <= residue_span_end")
        context = (
            self.context
            if isinstance(self.context, SummaryRecordContext)
            else SummaryRecordContext.from_dict(self.context)
        )
        object.__setattr__(
            self,
            "context",
            _with_defaults(
                context,
                storage_tier="feature_cache",
                planning_index_keys=DEFAULT_STRUCTURE_UNIT_PLANNING_KEYS,
                deferred_payloads=DEFAULT_STRUCTURE_UNIT_DEFERRED_PAYLOADS,
                lazy_loading_guidance=DEFAULT_STRUCTURE_UNIT_LAZY_GUIDANCE,
                storage_notes=(
                    "keep chain, entity, assembly, and span lineage visible",
                    "do not merge experimental and predicted structure summaries",
                ),
            ),
        )

    @property
    def record_type(self) -> SummaryRecordKind:
        return "structure_unit"

    @property
    def canonical_id(self) -> str:
        tokens = (
            self.structure_source,
            self.structure_id,
            self.entity_id or "",
            self.chain_id or "",
            self.assembly_id or "",
        )
        return ":".join(token for token in tokens if token)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "summary_id": self.summary_id,
            "protein_ref": self.protein_ref,
            "structure_source": self.structure_source,
            "structure_id": self.structure_id,
            "variant_ref": self.variant_ref,
            "structure_kind": self.structure_kind,
            "model_id": self.model_id,
            "entity_id": self.entity_id,
            "chain_id": self.chain_id,
            "assembly_id": self.assembly_id,
            "residue_span_start": self.residue_span_start,
            "residue_span_end": self.residue_span_end,
            "resolution_or_confidence": self.resolution_or_confidence,
            "experimental_or_predicted": self.experimental_or_predicted,
            "mapping_status": self.mapping_status,
            "structure_relation_notes": list(self.structure_relation_notes),
            "join_status": self.join_status,
            "join_reason": self.join_reason,
            "context": self.context.to_dict(),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> StructureUnitSummaryRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            summary_id=payload.get("summary_id") or payload.get("id") or "",
            protein_ref=payload.get("protein_ref") or payload.get("accession") or "",
            structure_source=payload.get("structure_source")
            or payload.get("source_name")
            or "",
            structure_id=payload.get("structure_id")
            or payload.get("pdb_id")
            or payload.get("model_id")
            or "",
            variant_ref=payload.get("variant_ref"),
            structure_kind=payload.get("structure_kind") or payload.get("kind") or "",
            model_id=payload.get("model_id"),
            entity_id=payload.get("entity_id"),
            chain_id=payload.get("chain_id"),
            assembly_id=payload.get("assembly_id"),
            residue_span_start=payload.get("residue_span_start")
            or payload.get("span_start"),
            residue_span_end=payload.get("residue_span_end")
            or payload.get("span_end"),
            resolution_or_confidence=payload.get("resolution_or_confidence")
            or payload.get("resolution")
            or payload.get("confidence"),
            experimental_or_predicted=payload.get("experimental_or_predicted")
            or payload.get("structure_mode")
            or "",
            mapping_status=payload.get("mapping_status")
            or payload.get("mapping_join_status")
            or "joined",
            structure_relation_notes=payload.get("structure_relation_notes")
            or payload.get("relation_notes")
            or (),
            join_status=payload.get("join_status") or payload.get("status") or "joined",
            join_reason=payload.get("join_reason") or payload.get("reason") or "",
            context=SummaryRecordContext.from_dict(payload.get("context") or {}),
            notes=payload.get("notes") or (),
        )


@dataclass(frozen=True, slots=True)
class ProteinLigandSummaryRecord:
    summary_id: str
    protein_ref: str
    ligand_ref: str
    association_type: str = ""
    association_id: str | None = None
    interaction_refs: tuple[str, ...] = ()
    assay_refs: tuple[str, ...] = ()
    organism_name: str = ""
    taxon_id: int | None = None
    measurement_type: str | None = None
    measurement_value: float | None = None
    measurement_unit: str | None = None
    confidence: float | None = None
    join_status: JoinStatus = "joined"
    join_reason: str = ""
    context: SummaryRecordContext = field(default_factory=SummaryRecordContext)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary_id", _clean_text(self.summary_id))
        object.__setattr__(self, "protein_ref", _clean_text(self.protein_ref))
        object.__setattr__(self, "ligand_ref", _clean_text(self.ligand_ref))
        object.__setattr__(self, "association_type", _clean_text(self.association_type))
        object.__setattr__(self, "association_id", _optional_text(self.association_id))
        object.__setattr__(self, "interaction_refs", _clean_text_tuple(self.interaction_refs))
        object.__setattr__(self, "assay_refs", _clean_text_tuple(self.assay_refs))
        object.__setattr__(self, "organism_name", _clean_text(self.organism_name))
        object.__setattr__(self, "taxon_id", _normalize_int(self.taxon_id, "taxon_id"))
        object.__setattr__(self, "measurement_type", _optional_text(self.measurement_type))
        object.__setattr__(
            self,
            "measurement_value",
            _normalize_float(self.measurement_value, "measurement_value"),
        )
        object.__setattr__(self, "measurement_unit", _optional_text(self.measurement_unit))
        object.__setattr__(self, "confidence", _normalize_float(self.confidence, "confidence"))
        object.__setattr__(self, "join_status", _normalize_join_status(self.join_status))
        object.__setattr__(self, "join_reason", _clean_text(self.join_reason))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.summary_id:
            raise ValueError("summary_id must not be empty")
        if not self.protein_ref:
            raise ValueError("protein_ref must not be empty")
        if not self.ligand_ref:
            raise ValueError("ligand_ref must not be empty")
        context = (
            self.context
            if isinstance(self.context, SummaryRecordContext)
            else SummaryRecordContext.from_dict(self.context)
        )
        object.__setattr__(
            self,
            "context",
            _with_defaults(
                context,
                storage_tier="feature_cache",
                planning_index_keys=DEFAULT_LIGAND_PLANNING_KEYS,
                deferred_payloads=DEFAULT_LIGAND_DEFERRED_PAYLOADS,
                lazy_loading_guidance=DEFAULT_LIGAND_LAZY_GUIDANCE,
                storage_notes=(
                    "keep target and ligand identity separate",
                    "hydrate assay rows and publication context only after selection",
                ),
            ),
        )

    @property
    def record_type(self) -> SummaryRecordKind:
        return "protein_ligand"

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "summary_id": self.summary_id,
            "protein_ref": self.protein_ref,
            "ligand_ref": self.ligand_ref,
            "association_type": self.association_type,
            "association_id": self.association_id,
            "interaction_refs": list(self.interaction_refs),
            "assay_refs": list(self.assay_refs),
            "organism_name": self.organism_name,
            "taxon_id": self.taxon_id,
            "measurement_type": self.measurement_type,
            "measurement_value": self.measurement_value,
            "measurement_unit": self.measurement_unit,
            "confidence": self.confidence,
            "join_status": self.join_status,
            "join_reason": self.join_reason,
            "context": self.context.to_dict(),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProteinLigandSummaryRecord:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            summary_id=payload.get("summary_id") or payload.get("id") or "",
            protein_ref=payload.get("protein_ref") or payload.get("target_ref") or "",
            ligand_ref=payload.get("ligand_ref") or payload.get("compound_ref") or "",
            association_type=payload.get("association_type") or payload.get("kind") or "",
            association_id=payload.get("association_id") or payload.get("pair_id"),
            interaction_refs=payload.get("interaction_refs")
            or payload.get("interaction_ids")
            or (),
            assay_refs=payload.get("assay_refs") or payload.get("assays") or (),
            organism_name=payload.get("organism_name") or payload.get("organism") or "",
            taxon_id=payload.get("taxon_id") or payload.get("tax_id"),
            measurement_type=payload.get("measurement_type"),
            measurement_value=payload.get("measurement_value"),
            measurement_unit=payload.get("measurement_unit"),
            confidence=payload.get("confidence"),
            join_status=payload.get("join_status") or payload.get("status") or "joined",
            join_reason=payload.get("join_reason") or payload.get("reason") or "",
            context=SummaryRecordContext.from_dict(payload.get("context") or {}),
            notes=payload.get("notes") or (),
        )


SummaryRecord = (
    ProteinSummaryRecord
    | ProteinVariantSummaryRecord
    | StructureUnitSummaryRecord
    | ProteinProteinSummaryRecord
    | ProteinLigandSummaryRecord
)


def _record_from_dict(payload: Mapping[str, Any]) -> SummaryRecord:
    record_type = _clean_text(payload.get("record_type") or payload.get("type")).casefold()
    if record_type in {"protein", "protein_summary"}:
        return ProteinSummaryRecord.from_dict(payload)
    if record_type in {"protein_variant", "protein-variant", "variant"}:
        return ProteinVariantSummaryRecord.from_dict(payload)
    if record_type in {"structure_unit", "structure-unit", "structure"}:
        return StructureUnitSummaryRecord.from_dict(payload)
    if record_type in {"protein_protein", "protein-protein", "pair", "interaction"}:
        return ProteinProteinSummaryRecord.from_dict(payload)
    if record_type in {"protein_ligand", "protein-ligand", "ligand", "association"}:
        return ProteinLigandSummaryRecord.from_dict(payload)
    raise ValueError(f"unsupported record_type: {payload.get('record_type')!r}")


def _summary_record_to_dict(record: SummaryRecord) -> dict[str, Any]:
    if isinstance(record, ProteinSummaryRecord):
        return record.to_dict()
    if isinstance(record, ProteinVariantSummaryRecord):
        return record.to_dict()
    if isinstance(record, StructureUnitSummaryRecord):
        return record.to_dict()
    if isinstance(record, ProteinProteinSummaryRecord):
        return record.to_dict()
    if isinstance(record, ProteinLigandSummaryRecord):
        return record.to_dict()
    raise TypeError(f"unsupported summary record type: {type(record)!r}")


@dataclass(frozen=True, slots=True)
class SummaryLibrarySchema:
    library_id: str
    records: tuple[SummaryRecord, ...]
    schema_version: int = 1
    source_manifest_id: str | None = None
    index_guidance: tuple[str, ...] = ()
    storage_guidance: tuple[str, ...] = ()
    lazy_loading_guidance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "library_id", _clean_text(self.library_id))
        object.__setattr__(self, "source_manifest_id", _optional_text(self.source_manifest_id))
        object.__setattr__(self, "index_guidance", _clean_text_tuple(self.index_guidance))
        object.__setattr__(self, "storage_guidance", _clean_text_tuple(self.storage_guidance))
        object.__setattr__(
            self,
            "lazy_loading_guidance",
            _clean_text_tuple(self.lazy_loading_guidance),
        )
        if not self.library_id:
            raise ValueError("library_id must not be empty")
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")

        normalized_records: list[SummaryRecord] = []
        seen_summary_ids: set[str] = set()
        for record in self.records:
            if not isinstance(
                record,
                (
                    ProteinSummaryRecord,
                    ProteinVariantSummaryRecord,
                    StructureUnitSummaryRecord,
                    ProteinProteinSummaryRecord,
                    ProteinLigandSummaryRecord,
                ),
            ):
                raise TypeError("records must contain summary record objects")
            if record.summary_id in seen_summary_ids:
                raise ValueError(f"duplicate summary_id: {record.summary_id}")
            seen_summary_ids.add(record.summary_id)
            normalized_records.append(record)
        object.__setattr__(self, "records", tuple(normalized_records))

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def protein_records(self) -> tuple[ProteinSummaryRecord, ...]:
        return tuple(record for record in self.records if isinstance(record, ProteinSummaryRecord))

    @property
    def pair_records(self) -> tuple[ProteinProteinSummaryRecord, ...]:
        return tuple(
            record for record in self.records if isinstance(record, ProteinProteinSummaryRecord)
        )

    @property
    def variant_records(self) -> tuple[ProteinVariantSummaryRecord, ...]:
        return tuple(
            record for record in self.records if isinstance(record, ProteinVariantSummaryRecord)
        )

    @property
    def structure_unit_records(self) -> tuple[StructureUnitSummaryRecord, ...]:
        return tuple(
            record for record in self.records if isinstance(record, StructureUnitSummaryRecord)
        )

    @property
    def ligand_records(self) -> tuple[ProteinLigandSummaryRecord, ...]:
        return tuple(
            record for record in self.records if isinstance(record, ProteinLigandSummaryRecord)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "library_id": self.library_id,
            "schema_version": self.schema_version,
            "source_manifest_id": self.source_manifest_id,
            "record_count": self.record_count,
            "index_guidance": list(self.index_guidance),
            "storage_guidance": list(self.storage_guidance),
            "lazy_loading_guidance": list(self.lazy_loading_guidance),
            "records": [_summary_record_to_dict(record) for record in self.records],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SummaryLibrarySchema:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            library_id=payload.get("library_id") or payload.get("id") or "",
            records=tuple(
                _record_from_dict(item) if isinstance(item, Mapping) else item
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


__all__ = [
    "DEFAULT_LIGAND_DEFERRED_PAYLOADS",
    "DEFAULT_LIGAND_LAZY_GUIDANCE",
    "DEFAULT_LIGAND_PLANNING_KEYS",
    "DEFAULT_PAIR_DEFERRED_PAYLOADS",
    "DEFAULT_PAIR_LAZY_GUIDANCE",
    "DEFAULT_PAIR_PLANNING_KEYS",
    "DEFAULT_PROTEIN_DEFERRED_PAYLOADS",
    "DEFAULT_PROTEIN_LAZY_GUIDANCE",
    "DEFAULT_PROTEIN_PLANNING_KEYS",
    "DEFAULT_STRUCTURE_UNIT_DEFERRED_PAYLOADS",
    "DEFAULT_STRUCTURE_UNIT_LAZY_GUIDANCE",
    "DEFAULT_STRUCTURE_UNIT_PLANNING_KEYS",
    "DEFAULT_VARIANT_DEFERRED_PAYLOADS",
    "DEFAULT_VARIANT_LAZY_GUIDANCE",
    "DEFAULT_VARIANT_PLANNING_KEYS",
    "ProteinLigandSummaryRecord",
    "ProteinProteinSummaryRecord",
    "ProteinSummaryRecord",
    "ProteinVariantSummaryRecord",
    "StructureUnitSummaryRecord",
    "SummaryBiologicalOrigin",
    "SummaryLibrarySchema",
    "SummaryProvenancePointer",
    "SummarySourceClaim",
    "SummarySourceConnection",
    "SummarySourceRollup",
    "SummaryRecord",
    "SummaryRecordContext",
    "SummaryRecordKind",
    "SummaryReference",
    "SummaryReferenceKind",
    "SummaryCrossSourceView",
    "SummaryStorageTier",
]
