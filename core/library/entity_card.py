from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

EntityCardKind = Literal["protein", "protein_protein", "protein_ligand"]
EntityCoverageState = Literal["release_ready", "nearly_ready", "partial", "blocked", "empty"]
EntityEvidenceDepth = Literal[
    "multilane_direct",
    "direct",
    "bridge_only",
    "probe_backed",
    "thin",
    "empty",
]

_CARD_KINDS = {"protein", "protein_protein", "protein_ligand"}
_COVERAGE_STATES = {"release_ready", "nearly_ready", "partial", "blocked", "empty"}
_EVIDENCE_DEPTHS = {
    "multilane_direct",
    "direct",
    "bridge_only",
    "probe_backed",
    "thin",
    "empty",
}


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


def _normalize_bool_or_none(value: Any, field_name: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool or None")
    return value


def _normalize_int_or_none(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer or None")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be an integer or None") from exc


def _normalize_float_or_none(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric or None")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be numeric or None") from exc


def _normalize_card_kind(value: Any) -> EntityCardKind:
    normalized = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    if normalized not in _CARD_KINDS:
        raise ValueError(f"unsupported entity_kind: {value!r}")
    return normalized  # type: ignore[return-value]


def _normalize_coverage_state(value: Any) -> EntityCoverageState:
    normalized = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    if normalized not in _COVERAGE_STATES:
        raise ValueError(f"unsupported coverage_state: {value!r}")
    return normalized  # type: ignore[return-value]


def _normalize_evidence_depth(value: Any) -> EntityEvidenceDepth:
    normalized = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    if normalized not in _EVIDENCE_DEPTHS:
        raise ValueError(f"unsupported evidence_depth: {value!r}")
    return normalized  # type: ignore[return-value]


def _default_evidence_summary() -> EntityCardEvidenceSummary:
    return EntityCardEvidenceSummary("partial", "thin")


@dataclass(frozen=True, slots=True)
class EntityCardEvidenceSummary:
    coverage_state: EntityCoverageState
    evidence_depth: EntityEvidenceDepth
    evidence_lanes: tuple[str, ...] = ()
    coverage_notes: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    packet_ready: bool | None = None
    release_score: int | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "coverage_state", _normalize_coverage_state(self.coverage_state))
        object.__setattr__(self, "evidence_depth", _normalize_evidence_depth(self.evidence_depth))
        object.__setattr__(self, "evidence_lanes", _clean_text_tuple(self.evidence_lanes))
        object.__setattr__(self, "coverage_notes", _clean_text_tuple(self.coverage_notes))
        object.__setattr__(self, "blocker_ids", _clean_text_tuple(self.blocker_ids))
        object.__setattr__(self, "provenance_refs", _clean_text_tuple(self.provenance_refs))
        object.__setattr__(
            self,
            "packet_ready",
            _normalize_bool_or_none(self.packet_ready, "packet_ready"),
        )
        object.__setattr__(
            self,
            "release_score",
            _normalize_int_or_none(self.release_score, "release_score"),
        )
        object.__setattr__(
            self,
            "confidence",
            _normalize_float_or_none(self.confidence, "confidence"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "coverage_state": self.coverage_state,
            "evidence_depth": self.evidence_depth,
            "evidence_lanes": list(self.evidence_lanes),
            "coverage_notes": list(self.coverage_notes),
            "blocker_ids": list(self.blocker_ids),
            "provenance_refs": list(self.provenance_refs),
            "packet_ready": self.packet_ready,
            "release_score": self.release_score,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EntityCardEvidenceSummary:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            coverage_state=payload.get("coverage_state") or "partial",
            evidence_depth=payload.get("evidence_depth") or "thin",
            evidence_lanes=payload.get("evidence_lanes") or (),
            coverage_notes=payload.get("coverage_notes") or payload.get("notes") or (),
            blocker_ids=payload.get("blocker_ids") or payload.get("blockers") or (),
            provenance_refs=payload.get("provenance_refs") or payload.get("evidence_refs") or (),
            packet_ready=payload.get("packet_ready"),
            release_score=payload.get("release_score") or payload.get("score"),
            confidence=payload.get("confidence"),
        )


@dataclass(frozen=True, slots=True)
class BaseEntityCard:
    card_id: str
    entity_kind: EntityCardKind
    canonical_id: str
    title: str
    subtitle: str | None = None
    summary_record_ref: str | None = None
    evidence_summary: EntityCardEvidenceSummary = field(default_factory=_default_evidence_summary)
    related_entity_refs: tuple[str, ...] = ()
    trace_refs: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "card_id", _clean_text(self.card_id))
        object.__setattr__(self, "entity_kind", _normalize_card_kind(self.entity_kind))
        object.__setattr__(self, "canonical_id", _clean_text(self.canonical_id))
        object.__setattr__(self, "title", _clean_text(self.title))
        object.__setattr__(self, "subtitle", _optional_text(self.subtitle))
        object.__setattr__(self, "summary_record_ref", _optional_text(self.summary_record_ref))
        object.__setattr__(
            self,
            "evidence_summary",
            (
                self.evidence_summary
                if isinstance(self.evidence_summary, EntityCardEvidenceSummary)
                else EntityCardEvidenceSummary.from_dict(self.evidence_summary)
            ),
        )
        object.__setattr__(
            self,
            "related_entity_refs",
            _clean_text_tuple(self.related_entity_refs),
        )
        object.__setattr__(self, "trace_refs", _clean_text_tuple(self.trace_refs))
        object.__setattr__(self, "tags", _clean_text_tuple(self.tags))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.card_id:
            raise ValueError("card_id must not be empty")
        if not self.canonical_id:
            raise ValueError("canonical_id must not be empty")
        if not self.title:
            raise ValueError("title must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "entity_kind": self.entity_kind,
            "canonical_id": self.canonical_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "summary_record_ref": self.summary_record_ref,
            "evidence_summary": self.evidence_summary.to_dict(),
            "related_entity_refs": list(self.related_entity_refs),
            "trace_refs": list(self.trace_refs),
            "tags": list(self.tags),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ProteinEntityCard(BaseEntityCard):
    accession: str = ""
    organism_name: str | None = None
    gene_names: tuple[str, ...] = ()
    pathway_refs: tuple[str, ...] = ()
    motif_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.entity_kind != "protein":
            raise ValueError("ProteinEntityCard requires entity_kind='protein'")
        object.__setattr__(self, "accession", _clean_text(self.accession))
        object.__setattr__(self, "organism_name", _optional_text(self.organism_name))
        object.__setattr__(self, "gene_names", _clean_text_tuple(self.gene_names))
        object.__setattr__(self, "pathway_refs", _clean_text_tuple(self.pathway_refs))
        object.__setattr__(self, "motif_refs", _clean_text_tuple(self.motif_refs))
        if not self.accession:
            raise ValueError("accession must not be empty")

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "accession": self.accession,
                "organism_name": self.organism_name,
                "gene_names": list(self.gene_names),
                "pathway_refs": list(self.pathway_refs),
                "motif_refs": list(self.motif_refs),
            }
        )
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProteinEntityCard:
        return cls(
            card_id=payload.get("card_id") or payload.get("id") or "",
            entity_kind=payload.get("entity_kind") or "protein",
            canonical_id=payload.get("canonical_id") or "",
            title=payload.get("title") or "",
            subtitle=payload.get("subtitle"),
            summary_record_ref=payload.get("summary_record_ref"),
            evidence_summary=payload.get("evidence_summary") or {},
            related_entity_refs=payload.get("related_entity_refs") or (),
            trace_refs=payload.get("trace_refs") or (),
            tags=payload.get("tags") or (),
            notes=payload.get("notes") or (),
            accession=payload.get("accession") or "",
            organism_name=payload.get("organism_name"),
            gene_names=payload.get("gene_names") or (),
            pathway_refs=payload.get("pathway_refs") or (),
            motif_refs=payload.get("motif_refs") or (),
        )


@dataclass(frozen=True, slots=True)
class ProteinProteinEntityCard(BaseEntityCard):
    protein_a_ref: str = ""
    protein_b_ref: str = ""
    interaction_refs: tuple[str, ...] = ()
    curated_direct: bool | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.entity_kind != "protein_protein":
            raise ValueError("ProteinProteinEntityCard requires entity_kind='protein_protein'")
        object.__setattr__(self, "protein_a_ref", _clean_text(self.protein_a_ref))
        object.__setattr__(self, "protein_b_ref", _clean_text(self.protein_b_ref))
        object.__setattr__(self, "interaction_refs", _clean_text_tuple(self.interaction_refs))
        object.__setattr__(
            self,
            "curated_direct",
            _normalize_bool_or_none(self.curated_direct, "curated_direct"),
        )
        if not self.protein_a_ref:
            raise ValueError("protein_a_ref must not be empty")
        if not self.protein_b_ref:
            raise ValueError("protein_b_ref must not be empty")
        if self.protein_a_ref == self.protein_b_ref:
            raise ValueError("protein_a_ref and protein_b_ref must be different")

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "protein_a_ref": self.protein_a_ref,
                "protein_b_ref": self.protein_b_ref,
                "interaction_refs": list(self.interaction_refs),
                "curated_direct": self.curated_direct,
            }
        )
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProteinProteinEntityCard:
        return cls(
            card_id=payload.get("card_id") or payload.get("id") or "",
            entity_kind=payload.get("entity_kind") or "protein_protein",
            canonical_id=payload.get("canonical_id") or "",
            title=payload.get("title") or "",
            subtitle=payload.get("subtitle"),
            summary_record_ref=payload.get("summary_record_ref"),
            evidence_summary=payload.get("evidence_summary") or {},
            related_entity_refs=payload.get("related_entity_refs") or (),
            trace_refs=payload.get("trace_refs") or (),
            tags=payload.get("tags") or (),
            notes=payload.get("notes") or (),
            protein_a_ref=payload.get("protein_a_ref") or "",
            protein_b_ref=payload.get("protein_b_ref") or "",
            interaction_refs=payload.get("interaction_refs") or (),
            curated_direct=payload.get("curated_direct"),
        )


@dataclass(frozen=True, slots=True)
class ProteinLigandEntityCard(BaseEntityCard):
    protein_ref: str = ""
    ligand_ref: str = ""
    assay_refs: tuple[str, ...] = ()
    structure_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.entity_kind != "protein_ligand":
            raise ValueError("ProteinLigandEntityCard requires entity_kind='protein_ligand'")
        object.__setattr__(self, "protein_ref", _clean_text(self.protein_ref))
        object.__setattr__(self, "ligand_ref", _clean_text(self.ligand_ref))
        object.__setattr__(self, "assay_refs", _clean_text_tuple(self.assay_refs))
        object.__setattr__(self, "structure_refs", _clean_text_tuple(self.structure_refs))
        if not self.protein_ref:
            raise ValueError("protein_ref must not be empty")
        if not self.ligand_ref:
            raise ValueError("ligand_ref must not be empty")

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "protein_ref": self.protein_ref,
                "ligand_ref": self.ligand_ref,
                "assay_refs": list(self.assay_refs),
                "structure_refs": list(self.structure_refs),
            }
        )
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProteinLigandEntityCard:
        return cls(
            card_id=payload.get("card_id") or payload.get("id") or "",
            entity_kind=payload.get("entity_kind") or "protein_ligand",
            canonical_id=payload.get("canonical_id") or "",
            title=payload.get("title") or "",
            subtitle=payload.get("subtitle"),
            summary_record_ref=payload.get("summary_record_ref"),
            evidence_summary=payload.get("evidence_summary") or {},
            related_entity_refs=payload.get("related_entity_refs") or (),
            trace_refs=payload.get("trace_refs") or (),
            tags=payload.get("tags") or (),
            notes=payload.get("notes") or (),
            protein_ref=payload.get("protein_ref") or "",
            ligand_ref=payload.get("ligand_ref") or "",
            assay_refs=payload.get("assay_refs") or (),
            structure_refs=payload.get("structure_refs") or (),
        )


EntityCard = ProteinEntityCard | ProteinProteinEntityCard | ProteinLigandEntityCard


def entity_card_from_dict(payload: Mapping[str, Any]) -> EntityCard:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    entity_kind = _normalize_card_kind(payload.get("entity_kind") or payload.get("record_type"))
    if entity_kind == "protein":
        return ProteinEntityCard.from_dict(payload)
    if entity_kind == "protein_protein":
        return ProteinProteinEntityCard.from_dict(payload)
    return ProteinLigandEntityCard.from_dict(payload)


__all__ = [
    "BaseEntityCard",
    "EntityCard",
    "EntityCardEvidenceSummary",
    "EntityCardKind",
    "EntityCoverageState",
    "EntityEvidenceDepth",
    "ProteinEntityCard",
    "ProteinLigandEntityCard",
    "ProteinProteinEntityCard",
    "entity_card_from_dict",
]
