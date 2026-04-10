from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal

from connectors.uniprot.parsers import UniProtSequenceRecord, parse_uniprot_entry
from core.canonical.protein import CanonicalProtein
from core.canonical.registry import CanonicalEntityRegistry, UnresolvedCanonicalReference
from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)
from core.provenance.record import ProvenanceRecord, ProvenanceSource
from execution.acquire.uniprot_snapshot import UniProtSnapshot, UniProtSnapshotRecord
from normalization.conflicts.protein_rules import (
    ProteinConflict,
    ProteinMergeResult,
    merge_protein_records,
)

SOURCE_NAME = "UniProt"
TRANSFORMATION_STEP = "sequence_to_canonical_protein"
DEFAULT_PARSER_VERSION = "1.0"
SequenceIngestStatus = Literal["ready", "partial", "unresolved"]
SequenceMergeStatus = Literal["resolved", "ambiguous", "conflict", "unresolved"]


def _clean_text(value: object | None) -> str:
    return str(value or "").strip()


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


def _normalize_accession(value: object | None) -> str | None:
    text = _clean_text(value).upper()
    return text or None


def _normalize_sequence(value: object | None) -> str | None:
    text = "".join(str(value or "").split()).upper()
    return text or None


def _normalize_bool(value: object | None) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = _clean_text(value).casefold()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _normalize_int(value: object | None) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        return int(str(value).strip())
    except TypeError, ValueError:
        return None


def _normalize_float(value: object | None) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _source_release_payload(
    value: SourceReleaseManifest | Mapping[str, Any] | None,
) -> SourceReleaseManifest | None:
    if value is None:
        return None
    if isinstance(value, SourceReleaseManifest):
        return value
    if isinstance(value, Mapping):
        return validate_source_release_manifest_payload(dict(value))
    raise TypeError("source_release must be a SourceReleaseManifest or mapping")


def _looks_like_provenance_record(value: Any) -> bool:
    return isinstance(value, Mapping) and {
        "provenance_id",
        "source",
        "transformation_step",
    }.issubset(value.keys())


def _make_checksum(
    accession: str | None,
    sequence: str | None,
    source_id: str | None,
    input_index: int,
) -> str:
    text = "|".join([accession or "", sequence or "", source_id or "", str(input_index)])
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _make_provenance_id(accession: str | None, source_id: str | None, input_index: int) -> str:
    return "sequence:" + ":".join(
        [accession or "unresolved", source_id or "source", str(input_index)]
    )


def _coerce_provenance_record(
    value: Any,
    *,
    accession: str | None,
    source_name: str,
    source_release: SourceReleaseManifest | None,
    parser_version: str,
    input_index: int,
    source_kind: str,
    source_id: str | None,
    sequence: str | None,
    organism: str | None,
    protein_name: str,
    gene_names: tuple[str, ...],
    reviewed: bool | None,
    release: str | None,
    release_date: str | None,
    proteome_id: str | None,
    proteome_reference: bool | None,
    proteome_taxon_id: int | None,
    raw_payload: Mapping[str, Any] | None,
) -> ProvenanceRecord:
    if isinstance(value, ProvenanceRecord):
        return value
    if _looks_like_provenance_record(value):
        try:
            record = ProvenanceRecord.from_dict(value)
            return replace(record, metadata=_json_ready(value))
        except TypeError, ValueError:
            pass

    payload = _json_ready(value) if isinstance(value, Mapping) else {}
    if not isinstance(payload, dict):
        payload = {}
    if source_release is not None:
        payload.setdefault("source_release", source_release.to_dict())
    payload.setdefault("source_kind", source_kind)
    if accession is not None:
        payload.setdefault("accession", accession)
    if source_id is not None:
        payload.setdefault("source_id", source_id)
    if sequence is not None:
        payload.setdefault("sequence_length", len(sequence))
    if organism is not None:
        payload.setdefault("organism", organism)
    if protein_name:
        payload.setdefault("protein_name", protein_name)
    if gene_names:
        payload.setdefault("gene_names", list(gene_names))
    if reviewed is not None:
        payload.setdefault("reviewed", reviewed)
    if release is not None:
        payload.setdefault("release", release)
    if release_date is not None:
        payload.setdefault("release_date", release_date)
    if proteome_id is not None:
        payload.setdefault("proteome_id", proteome_id)
    if proteome_reference is not None:
        payload.setdefault("proteome_reference", proteome_reference)
    if proteome_taxon_id is not None:
        payload.setdefault("proteome_taxon_id", proteome_taxon_id)
    if raw_payload is not None:
        payload.setdefault("raw_payload", _json_ready(raw_payload))

    provenance_source = ProvenanceSource(
        source_name=source_name or SOURCE_NAME,
        acquisition_mode="derived",
        original_identifier=source_id or accession,
        release_version=source_release.release_version if source_release else release,
        snapshot_id=source_release.manifest_id if source_release else release_date,
    )
    parent_ids = tuple(
        _unique_text(
            _iter_values(payload.get("parent_ids")) + _iter_values(payload.get("source_ids"))
        )
    )
    provenance_id = _clean_text(payload.get("provenance_id")) or _make_provenance_id(
        accession,
        source_id,
        input_index,
    )
    checksum = _clean_text(payload.get("checksum")) or _make_checksum(
        accession,
        sequence,
        source_id,
        input_index,
    )
    return ProvenanceRecord(
        provenance_id=provenance_id,
        source=provenance_source,
        transformation_step=_clean_text(payload.get("transformation_step"))
        or "sequence_observation",
        acquired_at=_clean_text(payload.get("acquired_at")) or datetime.now(UTC).isoformat(),
        parser_version=_clean_text(payload.get("parser_version")) or parser_version,
        transformation_history=_unique_text(_iter_values(payload.get("transformation_history"))),
        parent_ids=parent_ids,
        run_id=_clean_text(payload.get("run_id")) or None,
        confidence=_normalize_float(payload.get("confidence")),
        checksum=checksum,
        raw_payload_pointer=_clean_text(payload.get("raw_payload_pointer")) or None,
        metadata=payload,
    )


def _normalize_record(record: Any) -> dict[str, Any]:
    if isinstance(record, UniProtSnapshotRecord):
        sequence = record.sequence
        return {
            "accession": record.accession or sequence.accession,
            "entry_name": sequence.entry_name,
            "name": sequence.protein_name,
            "organism": sequence.organism_name,
            "gene_names": sequence.gene_names,
            "sequence": sequence.sequence,
            "sequence_length": sequence.sequence_length,
            "reviewed": sequence.reviewed,
            "source": SOURCE_NAME,
            "source_id": sequence.entry_name or record.accession,
            "release": record.release,
            "release_date": record.release_date,
            "proteome_id": record.proteome_id,
            "proteome_reference": record.proteome_reference,
            "proteome_taxon_id": record.proteome_taxon_id,
            "provenance": record.provenance,
            "raw_payload": record.raw_entry,
            "source_kind": "uniprot_snapshot_record",
        }
    if isinstance(record, UniProtSequenceRecord):
        return {
            "accession": record.accession,
            "entry_name": record.entry_name,
            "name": record.protein_name,
            "organism": record.organism_name,
            "gene_names": record.gene_names,
            "sequence": record.sequence,
            "sequence_length": record.sequence_length,
            "reviewed": record.reviewed,
            "source": SOURCE_NAME,
            "source_id": record.entry_name or record.accession,
            "provenance": {},
            "raw_payload": record.to_dict(),
            "source_kind": "uniprot_sequence_record",
        }
    if isinstance(record, CanonicalProtein):
        return {
            "accession": record.accession,
            "entry_name": record.accession,
            "name": record.name,
            "organism": record.organism,
            "gene_names": record.gene_names,
            "sequence": record.sequence,
            "sequence_length": len(record.sequence),
            "reviewed": None,
            "source": record.source or SOURCE_NAME,
            "source_id": record.accession,
            "provenance": {},
            "raw_payload": record.to_dict(),
            "source_kind": "canonical_protein",
        }
    if not isinstance(record, Mapping):
        raise TypeError("sequence record must be a mapping or UniProt record")

    payload = dict(record)
    if "primaryAccession" in payload or "proteinDescription" in payload:
        parsed = parse_uniprot_entry(payload)
        return {
            "accession": parsed.accession,
            "entry_name": parsed.entry_name,
            "name": parsed.protein_name,
            "organism": parsed.organism_name,
            "gene_names": parsed.gene_names,
            "sequence": parsed.sequence,
            "sequence_length": parsed.sequence_length,
            "reviewed": parsed.reviewed,
            "source": SOURCE_NAME,
            "source_id": parsed.entry_name or parsed.accession,
            "provenance": {},
            "raw_payload": payload,
            "source_kind": "uniprot_entry_mapping",
        }

    sequence = payload.get("sequence")
    if isinstance(sequence, Mapping):
        sequence_text = sequence.get("value") or sequence.get("sequence")
        sequence_length = _normalize_int(sequence.get("length"))
        if sequence_length is None and sequence_text is not None:
            sequence_length = len(_normalize_sequence(sequence_text) or "")
    else:
        sequence_text = sequence
        sequence_length = _normalize_int(payload.get("sequence_length"))
        if sequence_length is None and sequence_text is not None:
            sequence_length = len(_normalize_sequence(sequence_text) or "")

    organism = payload.get("organism") or payload.get("organism_name") or payload.get("species")
    if isinstance(organism, Mapping):
        organism = organism.get("scientificName") or organism.get("commonName")
    gene_names = payload.get("gene_names") or payload.get("genes") or ()
    if isinstance(gene_names, str):
        gene_names = (gene_names,)

    return {
        "accession": _normalize_accession(
            payload.get("accession") or payload.get("primaryAccession") or payload.get("uniprot_id")
        ),
        "entry_name": _clean_text(
            payload.get("entry_name") or payload.get("uniProtkbId") or payload.get("source_id")
        ),
        "name": _clean_text(payload.get("name") or payload.get("protein_name")),
        "organism": _clean_text(organism),
        "gene_names": _unique_text(_iter_values(gene_names)),
        "sequence": _normalize_sequence(sequence_text),
        "sequence_length": sequence_length,
        "reviewed": _normalize_bool(payload.get("reviewed")),
        "source": _clean_text(payload.get("source")) or SOURCE_NAME,
        "source_id": _clean_text(
            payload.get("source_id")
            or payload.get("uniProtkbId")
            or payload.get("entry_name")
            or payload.get("accession")
        ),
        "release": _clean_text(payload.get("release") or payload.get("release_version")) or None,
        "release_date": _clean_text(payload.get("release_date")) or None,
        "proteome_id": _clean_text(payload.get("proteome_id")) or None,
        "proteome_reference": _normalize_bool(payload.get("proteome_reference")),
        "proteome_taxon_id": _normalize_int(payload.get("proteome_taxon_id")),
        "provenance": payload.get("provenance") or payload.get("provenance_record"),
        "raw_payload": payload,
        "source_kind": "mapping",
    }


def _observation_provenance_refs(provenance_record: ProvenanceRecord) -> tuple[str, ...]:
    return tuple(_unique_text((provenance_record.provenance_id, *provenance_record.parent_ids)))


def _records_and_release(
    records: object | None,
) -> tuple[tuple[Any, ...], SourceReleaseManifest | None]:
    if records is None:
        return (), None
    if isinstance(records, UniProtSnapshot):
        return tuple(records.records), _source_release_payload(records.source_release)
    if isinstance(records, Mapping):
        if "records" in records:
            return tuple(_iter_values(records.get("records"))), _source_release_payload(
                records.get("source_release")
            )
        return (records,), None
    if isinstance(records, (str, bytes)):
        return (records,), None
    if isinstance(records, Iterable):
        return tuple(records), None
    return (records,), None


@dataclass(frozen=True, slots=True)
class SequenceIngestObservation:
    accession: str | None
    entry_name: str
    name: str
    organism: str
    gene_names: tuple[str, ...]
    sequence: str | None
    sequence_length: int | None
    reviewed: bool | None
    source: str
    source_id: str | None
    source_kind: str
    release: str | None
    release_date: str | None
    proteome_id: str | None
    proteome_reference: bool | None
    proteome_taxon_id: int | None
    provenance_record: ProvenanceRecord
    provenance_refs: tuple[str, ...]
    raw_payload: Mapping[str, Any] = field(default_factory=dict)
    input_index: int = 0

    def to_merge_payload(self) -> dict[str, Any]:
        annotations = [
            label
            for label in (
                "reviewed"
                if self.reviewed is True
                else "unreviewed"
                if self.reviewed is False
                else "",
                f"release:{self.release}" if self.release else "",
                f"release_date:{self.release_date}" if self.release_date else "",
                f"proteome:{self.proteome_id}" if self.proteome_id else "",
                "reference_proteome" if self.proteome_reference is True else "",
                f"taxon:{self.proteome_taxon_id}" if self.proteome_taxon_id is not None else "",
            )
            if label
        ]
        return {
            "accession": self.accession,
            "sequence": self.sequence,
            "organism": self.organism,
            "name": self.name,
            "gene_names": self.gene_names,
            "description": self.name,
            "source": self.source,
            "aliases": _unique_text((self.entry_name, self.source_id)),
            "annotations": tuple(annotations),
            "provenance_refs": self.provenance_refs,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "entry_name": self.entry_name,
            "name": self.name,
            "organism": self.organism,
            "gene_names": list(self.gene_names),
            "sequence": self.sequence,
            "sequence_length": self.sequence_length,
            "reviewed": self.reviewed,
            "source": self.source,
            "source_id": self.source_id,
            "source_kind": self.source_kind,
            "release": self.release,
            "release_date": self.release_date,
            "proteome_id": self.proteome_id,
            "proteome_reference": self.proteome_reference,
            "proteome_taxon_id": self.proteome_taxon_id,
            "provenance_record": self.provenance_record.to_dict(),
            "provenance_refs": list(self.provenance_refs),
            "raw_payload": _json_ready(self.raw_payload),
            "input_index": self.input_index,
        }


@dataclass(frozen=True, slots=True)
class SequenceIngestOutcome:
    accession: str | None
    status: SequenceMergeStatus
    reason: str
    observations: tuple[SequenceIngestObservation, ...]
    canonical_protein: CanonicalProtein | None
    provenance_record: ProvenanceRecord | None
    merge_result: ProteinMergeResult | None
    unresolved_reference: UnresolvedCanonicalReference | None = None
    conflicts: tuple[ProteinConflict, ...] = ()
    alternative_values: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "status": self.status,
            "reason": self.reason,
            "observations": [observation.to_dict() for observation in self.observations],
            "canonical_protein": (
                self.canonical_protein.to_dict() if self.canonical_protein is not None else None
            ),
            "provenance_record": (
                self.provenance_record.to_dict() if self.provenance_record is not None else None
            ),
            "merge_result": self.merge_result.to_dict() if self.merge_result is not None else None,
            "unresolved_reference": (
                self.unresolved_reference.to_dict()
                if self.unresolved_reference is not None
                else None
            ),
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "alternative_values": {
                key: list(values) for key, values in sorted(self.alternative_values.items())
            },
        }


@dataclass(frozen=True, slots=True)
class SequenceIngestResult:
    status: SequenceIngestStatus
    reason: str
    canonical_proteins: tuple[CanonicalProtein, ...]
    outcomes: tuple[SequenceIngestOutcome, ...]
    records: tuple[SequenceIngestObservation, ...]
    provenance_records: tuple[ProvenanceRecord, ...]
    unresolved_references: tuple[UnresolvedCanonicalReference, ...]
    conflicts: tuple[ProteinConflict, ...]
    source_release: dict[str, Any] = field(default_factory=dict)

    @property
    def observations(self) -> tuple[SequenceIngestObservation, ...]:
        return self.records

    @property
    def canonical_ids(self) -> tuple[str, ...]:
        return tuple(protein.canonical_id for protein in self.canonical_proteins)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "canonical_proteins": [protein.to_dict() for protein in self.canonical_proteins],
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
            "records": [record.to_dict() for record in self.records],
            "provenance_records": [record.to_dict() for record in self.provenance_records],
            "unresolved_references": [
                reference.to_dict() for reference in self.unresolved_references
            ],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "canonical_ids": list(self.canonical_ids),
            "source_release": dict(self.source_release),
        }


def ingest_sequence_records(
    records: object | None,
    *,
    registry: CanonicalEntityRegistry | None = None,
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
    parser_version: str = DEFAULT_PARSER_VERSION,
) -> SequenceIngestResult:
    raw_records, inferred_release = _records_and_release(records)
    release_manifest = _source_release_payload(source_release or inferred_release)

    observations: list[SequenceIngestObservation] = []
    for input_index, record in enumerate(raw_records):
        normalized = _normalize_record(record)
        provenance_record = _coerce_provenance_record(
            normalized.get("provenance"),
            accession=normalized.get("accession"),
            source_name=_clean_text(normalized.get("source")) or SOURCE_NAME,
            source_release=release_manifest,
            parser_version=parser_version,
            input_index=input_index,
            source_kind=_clean_text(normalized.get("source_kind")) or "mapping",
            source_id=normalized.get("source_id"),
            sequence=normalized.get("sequence"),
            organism=normalized.get("organism"),
            protein_name=_clean_text(normalized.get("name")),
            gene_names=tuple(normalized.get("gene_names") or ()),
            reviewed=normalized.get("reviewed"),
            release=normalized.get("release"),
            release_date=normalized.get("release_date"),
            proteome_id=normalized.get("proteome_id"),
            proteome_reference=normalized.get("proteome_reference"),
            proteome_taxon_id=normalized.get("proteome_taxon_id"),
            raw_payload=normalized.get("raw_payload"),
        )
        observations.append(
            SequenceIngestObservation(
                accession=normalized.get("accession"),
                entry_name=_clean_text(normalized.get("entry_name")),
                name=_clean_text(normalized.get("name")),
                organism=_clean_text(normalized.get("organism")),
                gene_names=tuple(normalized.get("gene_names") or ()),
                sequence=normalized.get("sequence"),
                sequence_length=_normalize_int(normalized.get("sequence_length")),
                reviewed=normalized.get("reviewed"),
                source=_clean_text(normalized.get("source")) or SOURCE_NAME,
                source_id=normalized.get("source_id"),
                source_kind=_clean_text(normalized.get("source_kind")) or "mapping",
                release=normalized.get("release"),
                release_date=normalized.get("release_date"),
                proteome_id=normalized.get("proteome_id"),
                proteome_reference=normalized.get("proteome_reference"),
                proteome_taxon_id=normalized.get("proteome_taxon_id"),
                provenance_record=provenance_record,
                provenance_refs=_observation_provenance_refs(provenance_record),
                raw_payload=normalized.get("raw_payload") or {},
                input_index=input_index,
            )
        )

    outcomes: list[SequenceIngestOutcome] = []
    canonical_proteins: list[CanonicalProtein] = []
    provenance_records: list[ProvenanceRecord] = []
    unresolved_references: list[UnresolvedCanonicalReference] = []
    conflicts: list[ProteinConflict] = []

    grouped: dict[str, list[SequenceIngestObservation]] = {}
    missing: list[SequenceIngestObservation] = []
    for observation in observations:
        if observation.accession:
            grouped.setdefault(observation.accession, []).append(observation)
        else:
            missing.append(observation)

    for observation in missing:
        unresolved = UnresolvedCanonicalReference(
            reference="<empty>",
            entity_type="protein",
            reason="missing_primary_identifier",
        )
        outcomes.append(
            SequenceIngestOutcome(
                accession=None,
                status="unresolved",
                reason="missing_primary_identifier",
                observations=(observation,),
                canonical_protein=None,
                provenance_record=None,
                merge_result=None,
                unresolved_reference=unresolved,
            )
        )
        unresolved_references.append(unresolved)

    for accession in sorted(grouped, key=str.casefold):
        group = tuple(sorted(grouped[accession], key=lambda item: item.input_index))
        merge_result, error_reason = _merge_group(group)
        if merge_result is None:
            unresolved = UnresolvedCanonicalReference(
                reference=accession,
                entity_type="protein",
                reason=error_reason or "unresolved",
            )
            outcomes.append(
                SequenceIngestOutcome(
                    accession=accession,
                    status="unresolved",
                    reason=error_reason or "unresolved",
                    observations=group,
                    canonical_protein=None,
                    provenance_record=None,
                    merge_result=None,
                    unresolved_reference=unresolved,
                )
            )
            unresolved_references.append(unresolved)
            continue

        canonical_provenance = _build_canonical_provenance(
            merge_result,
            group,
            release_manifest,
            parser_version,
        )
        if merge_result.canonical_protein is not None and registry is not None:
            try:
                registry.register(merge_result.canonical_protein)
            except ValueError as exc:
                unresolved = UnresolvedCanonicalReference(
                    reference=merge_result.canonical_protein.canonical_id,
                    entity_type="protein",
                    reason="registry_conflict",
                    candidates=(merge_result.canonical_protein.canonical_id,),
                )
                outcomes.append(
                    SequenceIngestOutcome(
                        accession=accession,
                        status="unresolved",
                        reason=f"registry_conflict: {exc}",
                        observations=group,
                        canonical_protein=None,
                        provenance_record=canonical_provenance,
                        merge_result=merge_result,
                        unresolved_reference=unresolved,
                        conflicts=merge_result.conflicts,
                        alternative_values=dict(merge_result.alternative_values),
                    )
                )
                unresolved_references.append(unresolved)
                conflicts.extend(merge_result.conflicts)
                continue

        unresolved = None
        if merge_result.canonical_protein is None:
            unresolved = UnresolvedCanonicalReference(
                reference=accession,
                entity_type="protein",
                reason=merge_result.reason,
            )
            unresolved_references.append(unresolved)

        outcomes.append(
            SequenceIngestOutcome(
                accession=accession,
                status=merge_result.status,
                reason=merge_result.reason,
                observations=group,
                canonical_protein=merge_result.canonical_protein,
                provenance_record=canonical_provenance,
                merge_result=merge_result,
                unresolved_reference=unresolved,
                conflicts=merge_result.conflicts,
                alternative_values=dict(merge_result.alternative_values),
            )
        )
        if merge_result.canonical_protein is not None:
            canonical_proteins.append(merge_result.canonical_protein)
            provenance_records.append(canonical_provenance)
        conflicts.extend(merge_result.conflicts)

    status, reason = _derive_status(outcomes)
    return SequenceIngestResult(
        status=status,
        reason=reason,
        canonical_proteins=tuple(canonical_proteins),
        outcomes=tuple(outcomes),
        records=tuple(observations),
        provenance_records=tuple(provenance_records),
        unresolved_references=tuple(unresolved_references),
        conflicts=tuple(conflicts),
        source_release=release_manifest.to_dict() if release_manifest is not None else {},
    )


def ingest_sequences(
    records: object | None,
    *,
    registry: CanonicalEntityRegistry | None = None,
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
    parser_version: str = DEFAULT_PARSER_VERSION,
) -> SequenceIngestResult:
    return ingest_sequence_records(
        records,
        registry=registry,
        source_release=source_release,
        parser_version=parser_version,
    )


def ingest_uniprot_snapshot(
    snapshot: UniProtSnapshot | Mapping[str, Any],
    *,
    registry: CanonicalEntityRegistry | None = None,
    parser_version: str = DEFAULT_PARSER_VERSION,
) -> SequenceIngestResult:
    if isinstance(snapshot, UniProtSnapshot):
        return ingest_sequence_records(
            snapshot.records,
            registry=registry,
            source_release=snapshot.source_release,
            parser_version=parser_version,
        )
    if not isinstance(snapshot, Mapping):
        raise TypeError("snapshot must be a UniProtSnapshot or mapping")
    return ingest_sequence_records(
        snapshot.get("records"),
        registry=registry,
        source_release=snapshot.get("source_release"),
        parser_version=parser_version,
    )


def _merge_group(
    group: tuple[SequenceIngestObservation, ...],
) -> tuple[ProteinMergeResult | None, str | None]:
    try:
        return merge_protein_records(observation.to_merge_payload() for observation in group), None
    except (TypeError, ValueError) as exc:
        accession = next(
            (observation.accession for observation in group if observation.accession), None
        )
        provenance_refs = tuple(
            _unique_text(ref for observation in group for ref in observation.provenance_refs)
        )
        conflict = ProteinConflict(
            field_name="sequence",
            kind="sequence_mismatch",
            observed_values=_unique_text(
                observation.sequence for observation in group if observation.sequence is not None
            ),
            message=f"sequence ingest could not normalize the group: {exc}",
        )
        return (
            ProteinMergeResult(
                status="unresolved",
                reason="invalid_sequence",
                canonical_protein=None,
                primary_accession=accession,
                sequence=next(
                    (observation.sequence for observation in group if observation.sequence), None
                ),
                organism=next(
                    (observation.organism for observation in group if observation.organism), None
                ),
                provenance_refs=provenance_refs,
                records=tuple(),
                conflicts=(conflict,),
            ),
            "invalid_sequence",
        )


def _build_canonical_provenance(
    merge_result: ProteinMergeResult,
    observations: tuple[SequenceIngestObservation, ...],
    source_release: SourceReleaseManifest | None,
    parser_version: str,
) -> ProvenanceRecord:
    source = observations[0].provenance_record
    parent_ids = tuple(
        _unique_text(ref for observation in observations for ref in observation.provenance_refs)
    )
    metadata = {
        "merge_status": merge_result.status,
        "merge_reason": merge_result.reason,
        "primary_accession": merge_result.primary_accession,
        "observed_accessions": [obs.accession for obs in observations if obs.accession],
        "observed_sequences": [obs.sequence for obs in observations if obs.sequence],
        "observed_organisms": [obs.organism for obs in observations if obs.organism],
        "source_provenance_ids": [obs.provenance_record.provenance_id for obs in observations],
        "source_release": source_release.to_dict() if source_release is not None else {},
        "alternative_values": {
            key: list(values) for key, values in sorted(merge_result.alternative_values.items())
        },
    }
    if merge_result.canonical_protein is not None:
        metadata["canonical_id"] = merge_result.canonical_protein.canonical_id
        metadata["sequence_length"] = merge_result.canonical_protein.sequence_length
    canonical = source.spawn_child(
        provenance_id=_make_canonical_provenance_id(merge_result, observations),
        transformation_step=TRANSFORMATION_STEP,
        parser_version=parser_version,
        checksum=_make_checksum(
            merge_result.primary_accession,
            merge_result.sequence,
            merge_result.primary_accession,
            observations[0].input_index,
        ),
        metadata=metadata,
    )
    return replace(
        canonical,
        parent_ids=parent_ids,
        transformation_history=(
            *source.transformation_history,
            source.transformation_step,
        ),
    )


def _make_canonical_provenance_id(
    merge_result: ProteinMergeResult,
    observations: tuple[SequenceIngestObservation, ...],
) -> str:
    source_ids = ",".join(obs.provenance_record.provenance_id for obs in observations)
    seed = "|".join(
        [merge_result.primary_accession or "unresolved", merge_result.sequence or "", source_ids]
    )
    digest = sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"sequence:{merge_result.primary_accession or 'unresolved'}:{digest}"


def _derive_status(outcomes: tuple[SequenceIngestOutcome, ...]) -> tuple[SequenceIngestStatus, str]:
    if not outcomes:
        return "unresolved", "no_sequence_records"
    has_resolved = any(outcome.canonical_protein is not None for outcome in outcomes)
    has_unresolved = any(outcome.status in {"conflict", "unresolved"} for outcome in outcomes)
    has_ambiguity = any(outcome.status == "ambiguous" for outcome in outcomes)
    if has_unresolved:
        return (
            "partial" if has_resolved else "unresolved"
        ), "sequence_records_include_unresolved_cases"
    if has_ambiguity:
        return "partial", "sequence_records_include_ambiguous_merges"
    return "ready", "sequence_records_resolved"


__all__ = [
    "DEFAULT_PARSER_VERSION",
    "SOURCE_NAME",
    "SequenceIngestObservation",
    "SequenceIngestOutcome",
    "SequenceIngestResult",
    "SequenceIngestStatus",
    "ingest_sequence_records",
    "ingest_sequences",
    "ingest_uniprot_snapshot",
]
