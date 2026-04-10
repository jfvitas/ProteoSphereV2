from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)
from core.storage.planning_index_schema import (
    JoinStatus,
    PlanningIndexCoverage,
    PlanningIndexEntry,
    PlanningIndexMaterializationPointer,
    PlanningIndexSchema,
    PlanningIndexSourceRecord,
)

InteractionKind = Literal["protein_protein", "protein_ligand"]


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


def _dedupe_text(values: Iterable[Any]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _coerce_mapping(record: Any) -> Mapping[str, Any]:
    if isinstance(record, Mapping):
        return record
    if hasattr(record, "to_dict") and callable(record.to_dict):
        payload = record.to_dict()
        if isinstance(payload, Mapping):
            return payload
    raise TypeError("records must contain mappings or source record objects")


def _coerce_source_release(
    value: SourceReleaseManifest | Mapping[str, Any] | None,
) -> SourceReleaseManifest | None:
    if value is None:
        return None
    if isinstance(value, SourceReleaseManifest):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("source_release must be a SourceReleaseManifest or mapping")
    return validate_source_release_manifest_payload(dict(value))


def _normalize_record_payload(
    record: Any,
) -> tuple[Mapping[str, Any], SourceReleaseManifest | None]:
    source_release: SourceReleaseManifest | None = None
    payload = record

    if isinstance(record, Mapping) and ("record" in record or "payload" in record):
        source_release = _coerce_source_release(record.get("source_release"))
        payload = record.get("record") or record.get("payload") or {}

    normalized_payload = _coerce_mapping(payload)
    return normalized_payload, source_release


def _source_name(payload: Mapping[str, Any], source_release: SourceReleaseManifest | None) -> str:
    if source_release is not None:
        return source_release.source_name
    for key in ("source_name", "source", "source_database"):
        text = _clean_text(payload.get(key))
        if text:
            return text
    provenance = payload.get("provenance")
    if isinstance(provenance, Mapping):
        text = _clean_text(provenance.get("source"))
        if text:
            return text
    return "interaction"


def _source_record_id(payload: Mapping[str, Any]) -> str:
    for key in (
        "interaction_ac",
        "Interaction AC",
        "biogrid_interaction_id",
        "BioGRID Interaction ID",
        "reactant_set_id",
        "BindingDB Reactant_set_id",
        "interaction_id",
        "source_record_id",
        "record_id",
        "identifier",
    ):
        text = _clean_text(payload.get(key))
        if text:
            return text
    return ""


def _manifest_id(
    source_name: str,
    source_record_id: str,
    source_release: SourceReleaseManifest | None,
) -> str:
    if source_release is not None:
        return source_release.manifest_id
    return f"{source_name}:{source_record_id or 'unreleased'}"


def _source_locator(
    payload: Mapping[str, Any],
    source_release: SourceReleaseManifest | None,
) -> str | None:
    if source_release is not None and source_release.source_locator:
        return source_release.source_locator
    for key in ("source_locator", "source_url", "url", "source"):
        text = _clean_text(payload.get(key))
        if text:
            return text
    provenance = payload.get("provenance")
    if isinstance(provenance, Mapping):
        text = _clean_text(provenance.get("source_locator"))
        if text:
            return text
    return None


def _extract_protein_candidates(
    payload: Mapping[str, Any],
    kind: InteractionKind,
) -> tuple[str, ...]:
    if kind == "protein_ligand":
        candidates = (
            payload.get("target_uniprot_ids"),
            payload.get("target_accession"),
            payload.get("protein_accession"),
            payload.get("participant_ids"),
            payload.get("participants"),
        )
        return _dedupe_text(
            value for candidate in candidates for value in _iter_values(candidate)
        )

    candidates = (
        payload.get("participant_a_ids"),
        payload.get("participant_b_ids"),
        payload.get("participant_ids"),
        payload.get("participants"),
        payload.get("protein_refs"),
    )
    protein_refs: list[str] = []
    for candidate in candidates:
        protein_refs.extend(
            _clean_text(value)
            for value in _iter_values(candidate)
            if _clean_text(value)
        )
    return _dedupe_text(protein_refs)


def _extract_ligand_candidates(payload: Mapping[str, Any]) -> tuple[str, ...]:
    candidates: list[str] = []

    for candidate in (
        payload.get("ligand_refs"),
        payload.get("ligand_id"),
        payload.get("monomer_id"),
        payload.get("BindingDB MonomerID"),
    ):
        candidates.extend(
            _clean_text(value)
            for value in _iter_values(candidate)
            if _clean_text(value)
        )

    for candidate in (
        payload.get("ligand_inchi_key"),
        payload.get("Ligand InChI Key"),
        payload.get("inchi_key"),
        payload.get("InChIKey"),
    ):
        for value in _iter_values(candidate):
            text = _clean_text(value)
            if not text:
                continue
            prefix = text.casefold()
            if prefix.startswith("inchikey=") or prefix.startswith("inchikey:"):
                text = text.split("=", 1)[-1].split(":", 1)[-1]
            candidates.append(f"ligand:inchikey:{text.upper()}")

    for candidate in (
        payload.get("ligand_smiles"),
        payload.get("Ligand SMILES"),
        payload.get("smiles"),
        payload.get("SMILES"),
    ):
        for value in _iter_values(candidate):
            text = _clean_text(value)
            if text:
                candidates.append(f"ligand:smiles:{text}")

    return _dedupe_text(candidates)


def _normalize_protein_ref(value: str) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.casefold().startswith("protein:"):
        accession = _clean_text(text.split(":", 1)[1]).upper()
        return f"protein:{accession}" if accession else None
    if text.casefold().startswith("uniprot:") or text.casefold().startswith("uniprotkb:"):
        accession = _clean_text(text.split(":", 1)[1]).upper()
        return f"protein:{accession}" if accession else None
    if ":" in text:
        return None
    accession = text.upper()
    if accession and any(char.isdigit() for char in accession):
        return f"protein:{accession}"
    return None


def _normalize_ligand_ref(value: str) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.casefold().startswith("ligand:"):
        ligand_id = _clean_text(text.split(":", 1)[1])
        return f"ligand:{ligand_id}" if ligand_id else None
    if text.casefold().startswith("bindingdb:"):
        ligand_id = _clean_text(text.split(":", 1)[1])
        return f"ligand:bindingdb:{ligand_id}" if ligand_id else None
    if text.casefold().startswith("inchikey:") or text.casefold().startswith("inchi_key:"):
        ligand_id = _clean_text(text.split(":", 1)[1]).upper()
        return f"ligand:inchikey:{ligand_id}" if ligand_id else None
    if text.casefold().startswith("smiles:"):
        ligand_id = _clean_text(text.split(":", 1)[1])
        return f"ligand:smiles:{ligand_id}" if ligand_id else None
    if ":" in text:
        return None
    return f"ligand:bindingdb:{text}"


def _resolve_protein_refs(candidates: tuple[str, ...]) -> tuple[str, ...]:
    return _dedupe_text(
        ref for candidate in candidates if (ref := _normalize_protein_ref(candidate)) is not None
    )


def _resolve_ligand_refs(candidates: tuple[str, ...]) -> tuple[str, ...]:
    return _dedupe_text(
        ref for candidate in candidates if (ref := _normalize_ligand_ref(candidate)) is not None
    )


def _interaction_kind(payload: Mapping[str, Any], protein_refs: tuple[str, ...]) -> InteractionKind:
    for key in ("interaction_kind", "kind", "interaction_type", "projection_mode"):
        text = _clean_text(payload.get(key)).casefold().replace("-", "_").replace(" ", "_")
        if text in {"protein_protein", "ppi"}:
            return "protein_protein"
        if text in {"protein_ligand", "ligand"}:
            return "protein_ligand"
    if any(
        key in payload
        for key in (
            "ligand_id",
            "monomer_id",
            "reactant_set_id",
            "ligand_smiles",
            "Ligand SMILES",
            "smiles",
            "SMILES",
            "ligand_inchi_key",
            "Ligand InChI Key",
            "inchi_key",
            "InChIKey",
        )
    ):
        return "protein_ligand"
    if len(protein_refs) <= 1:
        if "target_uniprot_ids" in payload or "target_accession" in payload:
            return "protein_ligand"
        return "protein_protein"
    return "protein_protein"


def _join_status(
    *,
    kind: InteractionKind,
    protein_refs: tuple[str, ...],
    ligand_refs: tuple[str, ...],
    expanded_from_complex: bool,
    explicit_status: str | None,
) -> JoinStatus:
    if explicit_status:
        return explicit_status
    if kind == "protein_ligand":
        if protein_refs and ligand_refs:
            return "candidate"
        if protein_refs or ligand_refs:
            return "partial"
        return "unjoined"
    if len(protein_refs) > 2:
        return "ambiguous"
    if len(protein_refs) == 2:
        return "partial" if expanded_from_complex else "candidate"
    if len(protein_refs) == 1:
        return "partial"
    return "unjoined"


def _planning_id(
    *,
    kind: InteractionKind,
    source_name: str,
    source_record_id: str,
    protein_refs: tuple[str, ...],
    ligand_refs: tuple[str, ...],
) -> str:
    if kind == "protein_protein" and len(protein_refs) == 2:
        return f"interaction:protein_protein:{protein_refs[0]}|{protein_refs[1]}"
    if kind == "protein_ligand" and protein_refs and ligand_refs:
        return f"interaction:protein_ligand:{protein_refs[0]}|{ligand_refs[0]}"
    return f"interaction:{kind}:{source_name}:{source_record_id or 'unresolved'}"


def _supporting_source_refs(payload: Mapping[str, Any], source_record_id: str) -> tuple[str, ...]:
    refs: list[str] = []
    for key in (
        "interaction_ac",
        "imex_id",
        "BioGRID Interaction ID",
        "PMID",
        "DOI",
        "reactant_set_id",
        "monomer_id",
    ):
        text = _clean_text(payload.get(key))
        if text:
            refs.append(text)
    if source_record_id:
        refs.insert(0, source_record_id)
    return _dedupe_text(refs)


def _build_lazy_pointers(
    *,
    source_name: str,
    source_record_id: str,
    source_locator: str | None,
    source_release: SourceReleaseManifest | None,
    kind: InteractionKind,
    explicit_artifact_refs: tuple[str, ...],
) -> tuple[PlanningIndexMaterializationPointer, ...]:
    pointers: list[PlanningIndexMaterializationPointer] = []
    materialization_kind = "table"
    notes = (
        "hydrate the pinned interaction row on selection",
        "keep source-native identifiers visible",
    )
    if kind == "protein_protein":
        notes = (*notes, "preserve binary or projection lineage")
    if kind == "protein_ligand":
        notes = (*notes, "keep target and ligand provenance separate")

    targets = explicit_artifact_refs
    if not targets and source_locator:
        targets = (source_locator,)

    for target in targets:
        pointers.append(
            PlanningIndexMaterializationPointer(
                materialization_kind=materialization_kind,
                pointer=target,
                selector=source_record_id or None,
                source_name=source_name,
                source_record_id=source_record_id or None,
                notes=notes,
            )
        )

    if not pointers and source_release is not None and source_release.source_locator:
        pointers.append(
            PlanningIndexMaterializationPointer(
                materialization_kind=materialization_kind,
                pointer=source_release.source_locator,
                selector=source_record_id or None,
                source_name=source_name,
                source_record_id=source_record_id or None,
                notes=notes,
            )
        )
    return tuple(pointers)


@dataclass(frozen=True, slots=True)
class InteractionPlanningRow:
    source_name: str
    source_record_id: str
    kind: InteractionKind
    planning_id: str
    protein_refs: tuple[str, ...] = field(default_factory=tuple)
    ligand_refs: tuple[str, ...] = field(default_factory=tuple)
    supporting_source_refs: tuple[str, ...] = field(default_factory=tuple)
    source_release: SourceReleaseManifest | None = None
    source_locator: str | None = None
    join_status: JoinStatus = "candidate"
    join_confidence: float | None = None
    expanded_from_complex: bool = False
    native_complex: bool = False
    raw_artifact_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_entry(self) -> PlanningIndexEntry:
        source_keys = {
            "interaction_kind": self.kind,
            "join_status": self.join_status,
            "protein_ref_count": str(len(self.protein_refs)),
            "ligand_ref_count": str(len(self.ligand_refs)),
            "expanded_from_complex": str(self.expanded_from_complex).lower(),
            "native_complex": str(self.native_complex).lower(),
        }
        if self.protein_refs:
            source_keys["protein_refs"] = "|".join(self.protein_refs)
        if self.ligand_refs:
            source_keys["ligand_refs"] = "|".join(self.ligand_refs)
        if self.supporting_source_refs:
            source_keys["supporting_source_refs"] = "|".join(self.supporting_source_refs)

        source_record = PlanningIndexSourceRecord(
            source_name=self.source_name,
            source_record_id=self.source_record_id,
            release_version=self.source_release.release_version if self.source_release else None,
            release_date=self.source_release.release_date if self.source_release else None,
            source_locator=self.source_locator,
            manifest_id=(
                self.source_release.manifest_id
                if self.source_release is not None
                else f"{self.source_name}:{self.source_record_id or 'unreleased'}"
            ),
            source_keys=source_keys,
        )
        coverage_state = (
            "partial"
            if self.join_status in {"partial", "ambiguous", "unjoined"}
            else "present"
        )
        coverage = (
            PlanningIndexCoverage(
                coverage_kind="source",
                label=self.source_name,
                coverage_state="present",
                source_names=(self.source_name,),
            ),
            PlanningIndexCoverage(
                coverage_kind="modality",
                label=self.kind,
                coverage_state=coverage_state,
                source_names=(self.source_name,),
                notes=(
                    "binary interaction planning",
                    (
                        "projection lineage preserved"
                        if self.expanded_from_complex
                        else "accession-first join"
                    ),
                ),
            ),
        )
        pointers = _build_lazy_pointers(
            source_name=self.source_name,
            source_record_id=self.source_record_id,
            source_locator=self.source_locator,
            source_release=self.source_release,
            kind=self.kind,
            explicit_artifact_refs=self.raw_artifact_refs,
        )
        metadata = {
            "interaction_kind": self.kind,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "protein_refs": self.protein_refs,
            "ligand_refs": self.ligand_refs,
            "supporting_source_refs": self.supporting_source_refs,
            "expanded_from_complex": self.expanded_from_complex,
            "native_complex": self.native_complex,
            "source_release": (
                None if self.source_release is None else self.source_release.to_dict()
            ),
            "source_locator": self.source_locator,
            "raw_artifact_refs": self.raw_artifact_refs,
        }
        metadata.update(self.metadata)
        return PlanningIndexEntry(
            planning_id=self.planning_id,
            source_records=(source_record,),
            canonical_ids=(self.planning_id,),
            join_status=self.join_status,
            join_confidence=self.join_confidence,
            coverage=coverage,
            lazy_materialization_pointers=pointers,
            metadata=metadata,
        )


def _row_from_record(
    record: Any,
    *,
    default_source_release: SourceReleaseManifest | None,
) -> InteractionPlanningRow:
    payload, inline_source_release = _normalize_record_payload(record)
    source_release = inline_source_release or default_source_release
    source_name = _source_name(payload, source_release)
    source_record_id = _source_record_id(payload)
    source_locator = _source_locator(payload, source_release)

    explicit_kind = payload.get("interaction_kind") or payload.get("kind") or payload.get(
        "interaction_type"
    )
    protein_candidates = _extract_protein_candidates(payload, "protein_ligand")
    ligand_candidates = _extract_ligand_candidates(payload)
    kind = _interaction_kind(payload, protein_candidates)
    if _clean_text(explicit_kind).casefold().replace("-", "_").replace(" ", "_") in {
        "protein_protein",
        "ppi",
    }:
        kind = "protein_protein"
    elif _clean_text(explicit_kind).casefold().replace("-", "_").replace(" ", "_") in {
        "protein_ligand",
        "ligand",
    }:
        kind = "protein_ligand"

    if kind == "protein_ligand":
        protein_refs = _resolve_protein_refs(protein_candidates)
        ligand_refs = _resolve_ligand_refs(ligand_candidates)
    else:
        raw_proteins: list[str] = []
        for key in (
            "participant_a_ids",
            "participant_b_ids",
            "participant_ids",
            "participants",
            "protein_refs",
        ):
            raw_proteins.extend(_dedupe_text(_iter_values(payload.get(key))))
        protein_refs = _resolve_protein_refs(tuple(raw_proteins))
        ligand_refs = ()

    supporting_source_refs = _supporting_source_refs(payload, source_record_id)
    expanded_from_complex = bool(payload.get("expanded_from_complex"))
    native_complex = bool(payload.get("native_complex"))
    explicit_status = _clean_text(payload.get("join_status") or payload.get("status")) or None
    join_status = _join_status(
        kind=kind,
        protein_refs=protein_refs,
        ligand_refs=ligand_refs,
        expanded_from_complex=expanded_from_complex,
        explicit_status=explicit_status,
    )
    if join_status == "unjoined" and (protein_refs or ligand_refs):
        join_status = "partial"

    planning_id = _planning_id(
        kind=kind,
        source_name=source_name,
        source_record_id=source_record_id,
        protein_refs=protein_refs,
        ligand_refs=ligand_refs,
    )
    join_confidence = payload.get("join_confidence") or payload.get("confidence")
    raw_artifact_refs = _dedupe_text(
        _iter_values(payload.get("raw_artifact_refs") or payload.get("artifact_refs"))
    )
    metadata = {
        "join_basis": "protein_accession" if protein_refs else "source_record",
        "participant_candidates": protein_candidates,
        "ligand_candidates": ligand_candidates,
        "source_payload_keys": tuple(sorted(payload.keys())),
        "source_record": {
            "source_name": source_name,
            "source_record_id": source_record_id,
            "source_locator": source_locator,
            "interaction_kind": kind,
        },
    }
    if payload.get("interaction_representation") is not None:
        metadata["interaction_representation"] = _clean_text(
            payload.get("interaction_representation")
        )
    if payload.get("interaction_ac") is not None:
        metadata["interaction_ac"] = _clean_text(payload.get("interaction_ac"))
    if payload.get("imex_id") is not None:
        metadata["imex_id"] = _clean_text(payload.get("imex_id"))
    if payload.get("reactant_set_id") is not None:
        metadata["reactant_set_id"] = _clean_text(payload.get("reactant_set_id"))
    if payload.get("monomer_id") is not None:
        metadata["monomer_id"] = _clean_text(payload.get("monomer_id"))

    return InteractionPlanningRow(
        source_name=source_name,
        source_record_id=source_record_id,
        kind=kind,
        planning_id=planning_id,
        protein_refs=protein_refs,
        ligand_refs=ligand_refs,
        supporting_source_refs=supporting_source_refs,
        source_release=source_release,
        source_locator=source_locator,
        join_status=join_status,
        join_confidence=join_confidence,
        expanded_from_complex=expanded_from_complex,
        native_complex=native_complex,
        raw_artifact_refs=raw_artifact_refs,
        metadata=metadata,
    )


def build_interaction_planning_entry(
    record: Any,
    *,
    default_source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
) -> PlanningIndexEntry:
    source_release = _coerce_source_release(default_source_release)
    return _row_from_record(record, default_source_release=source_release).to_entry()


def build_interaction_planning_index(
    records: object,
    *,
    default_source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
    schema_version: int = 1,
) -> PlanningIndexSchema:
    source_release = _coerce_source_release(default_source_release)
    if isinstance(records, (str, bytes)):
        raise TypeError("records must be an iterable of interaction records")
    if isinstance(records, Mapping):
        records = records.get("records") or records.get("entries") or (records,)
    if not isinstance(records, Iterable):
        raise TypeError("records must be iterable")

    entries = tuple(
        _row_from_record(item, default_source_release=source_release).to_entry()
        for item in records
    )
    return PlanningIndexSchema(records=entries, schema_version=schema_version)


__all__ = [
    "InteractionKind",
    "build_interaction_planning_entry",
    "build_interaction_planning_index",
]
