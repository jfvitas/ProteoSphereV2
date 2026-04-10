from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from core.canonical.protein import CanonicalProtein

ProteinMergeStatus = Literal["resolved", "ambiguous", "conflict", "unresolved"]
ProteinConflictKind = Literal[
    "accession_mismatch",
    "sequence_mismatch",
    "organism_mismatch",
    "missing_primary_identifier",
    "missing_sequence",
    "metadata_variation",
]

_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWYBXZJUO")
_DEFAULT_SOURCE_PRIORITY = ("UniProt",)


@dataclass(frozen=True, slots=True)
class ProteinObservation:
    accession: str | None
    sequence: str | None
    organism: str | None
    name: str
    gene_names: tuple[str, ...]
    description: str
    source: str
    aliases: tuple[str, ...]
    annotations: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    input_index: int

    def to_dict(self) -> dict[str, object]:
        return {
            "accession": self.accession,
            "sequence": self.sequence,
            "organism": self.organism,
            "name": self.name,
            "gene_names": list(self.gene_names),
            "description": self.description,
            "source": self.source,
            "aliases": list(self.aliases),
            "annotations": list(self.annotations),
            "provenance_refs": list(self.provenance_refs),
            "input_index": self.input_index,
        }


@dataclass(frozen=True, slots=True)
class ProteinConflict:
    field_name: str
    kind: ProteinConflictKind
    observed_values: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "kind": self.kind,
            "observed_values": list(self.observed_values),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ProteinMergeResult:
    status: ProteinMergeStatus
    reason: str
    canonical_protein: CanonicalProtein | None
    primary_accession: str | None
    sequence: str | None
    organism: str | None
    provenance_refs: tuple[str, ...]
    records: tuple[ProteinObservation, ...]
    conflicts: tuple[ProteinConflict, ...] = field(default_factory=tuple)
    alternative_values: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved" and self.canonical_protein is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "canonical_protein": (
                self.canonical_protein.to_dict() if self.canonical_protein is not None else None
            ),
            "primary_accession": self.primary_accession,
            "sequence": self.sequence,
            "organism": self.organism,
            "provenance_refs": list(self.provenance_refs),
            "records": [record.to_dict() for record in self.records],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "alternative_values": {
                field_name: list(values)
                for field_name, values in sorted(self.alternative_values.items())
            },
        }


def merge_protein_records(
    records: Iterable[object],
    *,
    source_priority: Sequence[str] = _DEFAULT_SOURCE_PRIORITY,
) -> ProteinMergeResult:
    observations = tuple(
        _normalize_observation(record, input_index=index)
        for index, record in enumerate(records)
    )
    provenance_refs = _merge_unique_values(
        ref for observation in observations for ref in observation.provenance_refs
    )

    if not observations:
        return ProteinMergeResult(
            status="unresolved",
            reason="no_records",
            canonical_protein=None,
            primary_accession=None,
            sequence=None,
            organism=None,
            provenance_refs=provenance_refs,
            records=(),
        )

    accessions = _merge_unique_values(
        observation.accession for observation in observations if observation.accession
    )
    if len(accessions) > 1:
        conflict = ProteinConflict(
            field_name="accession",
            kind="accession_mismatch",
            observed_values=accessions,
            message="records reference different primary protein accessions",
        )
        return ProteinMergeResult(
            status="conflict",
            reason="accession_mismatch",
            canonical_protein=None,
            primary_accession=None,
            sequence=None,
            organism=None,
            provenance_refs=provenance_refs,
            records=observations,
            conflicts=(conflict,),
            alternative_values={"accession": accessions},
        )

    primary_accession = accessions[0] if accessions else None
    sequence_values = _merge_unique_values(
        observation.sequence for observation in observations if observation.sequence
    )
    if len(sequence_values) > 1:
        conflict = ProteinConflict(
            field_name="sequence",
            kind="sequence_mismatch",
            observed_values=sequence_values,
            message="records contain incompatible protein sequences",
        )
        return ProteinMergeResult(
            status="conflict",
            reason="sequence_mismatch",
            canonical_protein=None,
            primary_accession=primary_accession,
            sequence=None,
            organism=None,
            provenance_refs=provenance_refs,
            records=observations,
            conflicts=(conflict,),
            alternative_values={"sequence": sequence_values},
        )

    sequence = sequence_values[0] if sequence_values else None
    if primary_accession is not None and sequence is None:
        conflict = ProteinConflict(
            field_name="sequence",
            kind="missing_sequence",
            observed_values=(),
            message="primary protein accession is present but no sequence was supplied",
        )
        return ProteinMergeResult(
            status="unresolved",
            reason="missing_sequence",
            canonical_protein=None,
            primary_accession=primary_accession,
            sequence=None,
            organism=None,
            provenance_refs=provenance_refs,
            records=observations,
            conflicts=(conflict,),
        )

    if primary_accession is None:
        conflict = ProteinConflict(
            field_name="accession",
            kind="missing_primary_identifier",
            observed_values=(),
            message="protein records do not provide a canonical primary accession",
        )
        return ProteinMergeResult(
            status="unresolved",
            reason="missing_primary_identifier",
            canonical_protein=None,
            primary_accession=None,
            sequence=sequence,
            organism=None,
            provenance_refs=provenance_refs,
            records=observations,
            conflicts=(conflict,),
        )

    organism_values = _merge_unique_values(
        observation.organism for observation in observations if observation.organism
    )
    if len(organism_values) > 1:
        conflict = ProteinConflict(
            field_name="organism",
            kind="organism_mismatch",
            observed_values=organism_values,
            message="records disagree on organism assignment",
        )
        return ProteinMergeResult(
            status="conflict",
            reason="organism_mismatch",
            canonical_protein=None,
            primary_accession=primary_accession,
            sequence=sequence,
            organism=None,
            provenance_refs=provenance_refs,
            records=observations,
            conflicts=(conflict,),
            alternative_values={"organism": organism_values},
        )

    organism = organism_values[0] if organism_values else ""
    representative = _select_representative_observation(
        observations,
        source_priority=source_priority,
    )
    resolved_name, name_values = _resolve_scalar_field(
        observations, "name", representative.name
    )
    resolved_description, description_values = _resolve_scalar_field(
        observations, "description", representative.description
    )
    resolved_source = representative.source

    gene_names = _merge_unique_values(
        gene_name for observation in observations for gene_name in observation.gene_names
    )
    aliases = _merge_unique_values(
        alias for observation in observations for alias in observation.aliases
    )
    annotations = _merge_unique_values(
        annotation for observation in observations for annotation in observation.annotations
    )

    alternative_values: dict[str, tuple[str, ...]] = {}
    if len(name_values) > 1:
        alternative_values["name"] = name_values
    if len(description_values) > 1:
        alternative_values["description"] = description_values
    status: ProteinMergeStatus = "resolved" if not alternative_values else "ambiguous"
    reason = "merged_cleanly" if status == "resolved" else "metadata_variation_preserved"

    canonical_protein = CanonicalProtein(
        accession=primary_accession,
        sequence=sequence,
        name=resolved_name,
        gene_names=gene_names,
        organism=organism,
        description=resolved_description,
        source=resolved_source or "UniProt",
        aliases=aliases,
        annotations=annotations,
    )
    return ProteinMergeResult(
        status=status,
        reason=reason,
        canonical_protein=canonical_protein,
        primary_accession=primary_accession,
        sequence=sequence,
        organism=organism,
        provenance_refs=provenance_refs,
        records=observations,
        alternative_values=alternative_values,
    )


def _normalize_observation(record: object, *, input_index: int) -> ProteinObservation:
    payload = _to_mapping(record)
    accession = _normalize_accession(
        _first_non_empty_value(payload, "accession", "uniprot_id", "primary_external_id")
    )
    sequence = _normalize_sequence(
        _first_non_empty_value(payload, "sequence", "canonical_sequence")
    )
    organism = _clean_text(
        _first_non_empty_value(payload, "organism", "organism_name", "species")
    )
    name = _clean_text(_first_non_empty_value(payload, "name", "protein_name"))
    gene_names = _normalize_string_tuple(_coerce_iterable(payload, "gene_names", "genes"))
    description = _clean_text(_first_non_empty_value(payload, "description"))
    source = _clean_text(_first_non_empty_value(payload, "source", "source_name")) or "UniProt"
    aliases = _normalize_string_tuple(_coerce_iterable(payload, "aliases"))
    annotations = _normalize_string_tuple(_coerce_iterable(payload, "annotations"))
    provenance_refs = _normalize_provenance_refs(payload)
    return ProteinObservation(
        accession=accession,
        sequence=sequence,
        organism=organism,
        name=name,
        gene_names=gene_names,
        description=description,
        source=source,
        aliases=aliases,
        annotations=annotations,
        provenance_refs=provenance_refs,
        input_index=input_index,
    )


def _resolve_scalar_field(
    observations: Sequence[ProteinObservation],
    field_name: str,
    representative_value: str,
) -> tuple[str, tuple[str, ...]]:
    values = _merge_unique_values(
        getattr(observation, field_name)
        for observation in observations
        if getattr(observation, field_name)
    )
    if values:
        return (representative_value or values[0], values)
    return representative_value, values


def _select_representative_observation(
    observations: Sequence[ProteinObservation],
    *,
    source_priority: Sequence[str],
) -> ProteinObservation:
    source_ranks = {
        _clean_text(source).casefold(): priority
        for priority, source in enumerate(source_priority)
        if _clean_text(source)
    }
    return min(
        observations,
        key=lambda observation: (
            source_ranks.get(observation.source.casefold(), len(source_ranks)),
            observation.input_index,
        ),
    )


def _to_mapping(record: object) -> Mapping[str, Any]:
    if isinstance(record, CanonicalProtein):
        return record.to_dict()
    if isinstance(record, Mapping):
        return record
    if hasattr(record, "__dict__"):
        return vars(record)
    raise TypeError("protein record must be a mapping or canonical protein instance")


def _first_non_empty_value(payload: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
        elif value is not None:
            cleaned = str(value).strip()
            if cleaned:
                return cleaned
    return ""


def _coerce_iterable(payload: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            return (value,)
        if isinstance(value, Iterable):
            return tuple(str(item) for item in value)
    return ()


def _normalize_provenance_refs(payload: Mapping[str, Any]) -> tuple[str, ...]:
    candidates: list[str] = []
    for key in ("provenance_refs", "provenance", "provenance_id"):
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            candidates.append(value)
            continue
        if isinstance(value, Iterable):
            candidates.extend(str(item) for item in value)
    return _normalize_string_tuple(candidates)


def _normalize_accession(value: str) -> str | None:
    cleaned = _clean_text(value).upper()
    return cleaned or None


def _normalize_sequence(value: str) -> str | None:
    cleaned = "".join(str(value).split()).upper()
    if not cleaned:
        return None
    invalid = sorted(set(cleaned) - _AMINO_ACIDS)
    if invalid:
        raise ValueError(
            "sequence contains invalid residue codes: " + ", ".join(invalid)
        )
    return cleaned


def _clean_text(value: str) -> str:
    return str(value).strip()


def _normalize_string_tuple(values: Iterable[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _clean_text(str(value))
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return tuple(cleaned)


def _merge_unique_values(values: Iterable[str]) -> tuple[str, ...]:
    return _normalize_string_tuple(values)


__all__ = [
    "ProteinConflict",
    "ProteinConflictKind",
    "ProteinMergeResult",
    "ProteinMergeStatus",
    "ProteinObservation",
    "merge_protein_records",
]
