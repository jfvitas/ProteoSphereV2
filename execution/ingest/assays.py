from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from connectors.bindingdb.parsers import (
    BindingDBAssayRecord,
    parse_bindingdb_assay_row,
    parse_bindingdb_assays,
)
from core.canonical.assay import CanonicalAssay
from core.canonical.registry import CanonicalEntityRegistry, UnresolvedCanonicalReference
from core.provenance.record import ProvenanceRecord, ProvenanceSource
from normalization.conflicts.assay_rules import AssayConflict, merge_assay_records

AssayIngestStatus = Literal["resolved", "ambiguous", "conflict", "unresolved"]
AssayIngestIssueKind = Literal[
    "missing_source_id",
    "missing_target_identifier",
    "target_ambiguity",
    "target_unresolved",
    "missing_ligand_identifier",
    "ligand_ambiguity",
    "ligand_unresolved",
    "missing_measurement_type",
    "missing_measurement_value",
    "assay_conflict",
]

_SOURCE_NAME = "BindingDB"
_REFERENCE_KEYS = (
    "pmid",
    "PMID",
    "PubMed ID",
    "pubmed_id",
    "doi",
    "DOI",
    "article_doi",
    "Article DOI",
    "bindingdb_entry_doi",
    "BindingDB Entry DOI",
)
_VALUE_RE = re.compile(
    r"^\s*(?P<relation><=|>=|<|>|=)?\s*(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _stable_checksum(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(_json_ready(dict(payload)), sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(blob.encode('utf-8')).hexdigest()}"


def _extract_reference_strings(raw: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not raw:
        return ()
    references: list[str] = []
    for key in _REFERENCE_KEYS:
        value = raw.get(key)
        text = _clean_text(value)
        if not text:
            continue
        prefix = "DOI" if "doi" in key.casefold() else "PMID"
        if not text.upper().startswith(f"{prefix}:"):
            text = f"{prefix}:{text}"
        references.append(text)
    return _dedupe(references)


def _extract_relation(raw: Mapping[str, Any] | None) -> str | None:
    if not raw:
        return None
    for key in (
        "affinity_value_nM",
        "affinity_value",
        "binding_affinity_value",
        "value",
        "measurement_value",
    ):
        text = _clean_text(raw.get(key))
        if not text:
            continue
        match = _VALUE_RE.match(text)
        if match and match.group("relation"):
            return match.group("relation")
    return None


def _source_name(source_name: str | None) -> str:
    return _clean_text(source_name) or _SOURCE_NAME


def _source_id(record: BindingDBAssayRecord) -> str | None:
    if record.raw:
        for key in ("bindingdb_source_id", "BindingDB Source ID", "source_id"):
            value = _clean_text(record.raw.get(key))
            if value:
                return value
    source_id = _clean_text(record.reactant_set_id)
    return source_id or None


def _protein_reference(
    accession: str | None,
    registry: CanonicalEntityRegistry | None,
) -> tuple[str | None, AssayIngestIssueKind | None, str | None, tuple[str, ...]]:
    if accession is None:
        return None, "missing_target_identifier", None, ()
    canonical_reference = f"protein:{accession}"
    if registry is None:
        return canonical_reference, None, None, ()
    resolved = registry.resolve(accession, entity_type="protein")
    if isinstance(resolved, UnresolvedCanonicalReference):
        if resolved.reason == "ambiguous":
            return None, "target_ambiguity", resolved.reason, resolved.candidates
        return None, "target_unresolved", resolved.reason, ()
    return registry.canonical_reference(resolved), None, None, ()


def _ligand_reference(
    monomer_id: str | None,
    registry: CanonicalEntityRegistry | None,
) -> tuple[str | None, AssayIngestIssueKind | None, str | None, tuple[str, ...]]:
    if monomer_id is None:
        return None, "missing_ligand_identifier", None, ()
    candidate_reference = f"bindingdb:{monomer_id}"
    if registry is None:
        return f"ligand:{candidate_reference}", None, None, ()
    resolved = registry.resolve(candidate_reference, entity_type="ligand")
    if isinstance(resolved, UnresolvedCanonicalReference):
        if resolved.reason == "ambiguous":
            return None, "ligand_ambiguity", resolved.reason, resolved.candidates
        return None, "ligand_unresolved", resolved.reason, ()
    return registry.canonical_reference(resolved), None, None, ()


def _consensus_text(values: Iterable[str | None]) -> str | None:
    cleaned = _dedupe(value for value in values if value is not None)
    return cleaned[0] if len(cleaned) == 1 else None


def _consensus_float(values: Iterable[float | None]) -> float | None:
    seen: list[float] = []
    for value in values:
        if value is None:
            continue
        if not seen:
            seen.append(float(value))
            continue
        if float(value) != seen[0]:
            return None
    return seen[0] if seen else None


def _payload_from_record(
    record: BindingDBAssayRecord,
    *,
    source_name: str,
    source_id: str,
    target_id: str,
    ligand_id: str,
    provenance_id: str,
) -> dict[str, Any]:
    return {
        "target_id": target_id,
        "ligand_id": ligand_id,
        "measurement_type": record.affinity_type,
        "measurement_value": record.affinity_value_nM,
        "measurement_unit": "nM" if record.affinity_value_nM is not None else None,
        "relation": _extract_relation(record.raw),
        "source": source_name,
        "source_id": source_id,
        "assay_conditions": record.assay_description,
        "ph": None,
        "temperature_celsius": None,
        "references": _extract_reference_strings(record.raw),
        "provenance_refs": (provenance_id,),
    }


@dataclass(frozen=True, slots=True)
class AssayIngestIssue:
    assay_key: str
    kind: AssayIngestIssueKind
    message: str
    input_indices: tuple[int, ...]
    source_ids: tuple[str, ...] = ()
    target_candidates: tuple[str, ...] = ()
    ligand_candidates: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    conflicts: tuple[AssayConflict, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "assay_key", _clean_text(self.assay_key))
        object.__setattr__(self, "message", _clean_text(self.message))
        object.__setattr__(self, "input_indices", tuple(dict.fromkeys(self.input_indices)))
        object.__setattr__(self, "source_ids", _dedupe(self.source_ids))
        object.__setattr__(self, "target_candidates", _dedupe(self.target_candidates))
        object.__setattr__(self, "ligand_candidates", _dedupe(self.ligand_candidates))
        object.__setattr__(self, "provenance_ids", _dedupe(self.provenance_ids))
        object.__setattr__(self, "conflicts", tuple(self.conflicts))

    def to_dict(self) -> dict[str, object]:
        return {
            "assay_key": self.assay_key,
            "kind": self.kind,
            "message": self.message,
            "input_indices": list(self.input_indices),
            "source_ids": list(self.source_ids),
            "target_candidates": list(self.target_candidates),
            "ligand_candidates": list(self.ligand_candidates),
            "provenance_ids": list(self.provenance_ids),
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


@dataclass(frozen=True, slots=True)
class AssayIngestCase:
    assay_key: str
    status: AssayIngestStatus
    canonical_assay: CanonicalAssay | None
    provenance_records: tuple[ProvenanceRecord, ...]
    observations: tuple[BindingDBAssayRecord, ...]
    issues: tuple[AssayIngestIssue, ...] = ()
    conflicts: tuple[AssayConflict, ...] = ()
    alternative_values: dict[str, tuple[str, ...]] = field(default_factory=dict)
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "assay_key", _clean_text(self.assay_key))
        object.__setattr__(self, "reason", _clean_text(self.reason))
        object.__setattr__(self, "provenance_records", tuple(self.provenance_records))
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "conflicts", tuple(self.conflicts))
        object.__setattr__(
            self,
            "alternative_values",
            {key: _dedupe(values) for key, values in sorted(self.alternative_values.items())},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "assay_key": self.assay_key,
            "status": self.status,
            "canonical_assay": (
                None if self.canonical_assay is None else self.canonical_assay.to_dict()
            ),
            "provenance_records": [record.to_dict() for record in self.provenance_records],
            "observations": [record.to_dict() for record in self.observations],
            "issues": [issue.to_dict() for issue in self.issues],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "alternative_values": {
                key: list(values) for key, values in self.alternative_values.items()
            },
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AssayIngestResult:
    status: AssayIngestStatus
    reason: str
    cases: tuple[AssayIngestCase, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", _clean_text(self.reason))
        object.__setattr__(self, "cases", tuple(self.cases))

    @property
    def canonical_assays(self) -> tuple[CanonicalAssay, ...]:
        return tuple(
            case.canonical_assay
            for case in self.cases
            if case.canonical_assay is not None
        )

    @property
    def provenance_records(self) -> tuple[ProvenanceRecord, ...]:
        return tuple(
            provenance_record
            for case in self.cases
            for provenance_record in case.provenance_records
        )

    @property
    def unresolved_cases(self) -> tuple[AssayIngestCase, ...]:
        return tuple(case for case in self.cases if case.status != "resolved")

    @property
    def conflicts(self) -> tuple[AssayConflict, ...]:
        return tuple(conflict for case in self.cases for conflict in case.conflicts)

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved" and not self.unresolved_cases

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "cases": [case.to_dict() for case in self.cases],
            "canonical_assays": [assay.to_dict() for assay in self.canonical_assays],
            "provenance_records": [record.to_dict() for record in self.provenance_records],
            "unresolved_cases": [case.to_dict() for case in self.unresolved_cases],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


def ingest_assay_records(
    records: (
        Iterable[BindingDBAssayRecord | Mapping[str, Any]]
        | BindingDBAssayRecord
        | Mapping[str, Any]
    ),
    *,
    registry: CanonicalEntityRegistry | None = None,
    source_name: str = _SOURCE_NAME,
    acquisition_mode: str = "derived",
    acquired_at: str | None = None,
    parser_version: str | None = None,
    release_version: str | None = None,
    run_id: str | None = None,
) -> AssayIngestResult:
    bindingdb_records = _coerce_bindingdb_records(records, source_name=source_name)
    normalized_source_name = _source_name(source_name)

    if not bindingdb_records:
        empty_issue = AssayIngestIssue(
            assay_key=f"{normalized_source_name}:<empty>",
            kind="missing_source_id",
            message="no assay records were supplied",
            input_indices=(),
        )
        empty_case = AssayIngestCase(
            assay_key=empty_issue.assay_key,
            status="unresolved",
            canonical_assay=None,
            provenance_records=(),
            observations=(),
            issues=(empty_issue,),
            conflicts=(),
            alternative_values={},
            reason="no_records",
        )
        return AssayIngestResult(
            status="unresolved",
            reason="no_records",
            cases=(empty_case,),
        )

    grouped: dict[str, list[tuple[int, BindingDBAssayRecord]]] = defaultdict(list)
    unresolved_cases: list[AssayIngestCase] = []
    for input_index, record in enumerate(bindingdb_records):
        source_id = _source_id(record)
        if source_id is None:
            issue = AssayIngestIssue(
                assay_key=f"{normalized_source_name}:input-{input_index + 1}",
                kind="missing_source_id",
                message=(
                    "BindingDB assay rows require a reactant_set_id "
                    "to form a canonical assay id"
                ),
                input_indices=(input_index,),
                target_candidates=tuple(record.target_uniprot_ids),
                ligand_candidates=(record.monomer_id,) if record.monomer_id else (),
            )
            unresolved_cases.append(
                AssayIngestCase(
                    assay_key=issue.assay_key,
                    status="unresolved",
                    canonical_assay=None,
                    provenance_records=(
                        _build_provenance_record(
                            record,
                            input_index=input_index,
                            source_name=normalized_source_name,
                            source_id=f"input-{input_index + 1}",
                            acquired_at=acquired_at,
                            acquisition_mode=acquisition_mode,
                            parser_version=parser_version,
                            release_version=release_version,
                            run_id=run_id,
                        ),
                    ),
                    observations=(record,),
                    issues=(issue,),
                    conflicts=(),
                    alternative_values={},
                    reason="missing_source_id",
                )
            )
            continue
        grouped[f"{normalized_source_name}:{source_id}"].append((input_index, record))

    cases: list[AssayIngestCase] = []
    cases.extend(unresolved_cases)
    for assay_key, indexed_records in grouped.items():
        case = _ingest_assay_group(
            assay_key,
            indexed_records,
            registry=registry,
            source_name=normalized_source_name,
            acquired_at=acquired_at,
            acquisition_mode=acquisition_mode,
            parser_version=parser_version,
            release_version=release_version,
            run_id=run_id,
        )
        cases.append(case)

    status = _batch_status(cases)
    reason = _batch_reason(status, cases)
    return AssayIngestResult(status=status, reason=reason, cases=tuple(cases))


def ingest_bindingdb_assays(
    records: (
        Iterable[BindingDBAssayRecord | Mapping[str, Any]]
        | BindingDBAssayRecord
        | Mapping[str, Any]
    ),
    **kwargs: Any,
) -> AssayIngestResult:
    return ingest_assay_records(records, **kwargs)


def ingest_assays_to_canonical_layer(
    records: (
        Iterable[BindingDBAssayRecord | Mapping[str, Any]]
        | BindingDBAssayRecord
        | Mapping[str, Any]
    ),
    **kwargs: Any,
) -> AssayIngestResult:
    return ingest_assay_records(records, **kwargs)


def _coerce_bindingdb_records(
    records: (
        Iterable[BindingDBAssayRecord | Mapping[str, Any]]
        | BindingDBAssayRecord
        | Mapping[str, Any]
    ),
    *,
    source_name: str,
) -> tuple[BindingDBAssayRecord, ...]:
    if isinstance(records, BindingDBAssayRecord):
        return (records,)
    if isinstance(records, Mapping):
        return tuple(parse_bindingdb_assays([records], source=source_name))
    if isinstance(records, (str, bytes)):
        raise TypeError("records must be bindingdb assay rows, not a string")
    if not isinstance(records, Iterable):
        raise TypeError("records must be iterable or a BindingDB assay record")

    rows = list(records)
    if not rows:
        return ()
    if all(isinstance(row, BindingDBAssayRecord) for row in rows):
        return tuple(rows)
    if all(isinstance(row, Mapping) for row in rows):
        return tuple(parse_bindingdb_assays(rows, source=source_name))
    raise TypeError("records must contain either mappings or BindingDBAssayRecord instances")


def _ingest_assay_group(
    assay_key: str,
    indexed_records: list[tuple[int, BindingDBAssayRecord]],
    *,
    registry: CanonicalEntityRegistry | None,
    source_name: str,
    acquired_at: str | None,
    acquisition_mode: str,
    parser_version: str | None,
    release_version: str | None,
    run_id: str | None,
) -> AssayIngestCase:
    payloads: list[dict[str, Any]] = []
    provenance_records: list[ProvenanceRecord] = []
    issues: list[AssayIngestIssue] = []

    for input_index, record in indexed_records:
        source_id = _source_id(record)
        assert source_id is not None

        provenance_record = _build_provenance_record(
            record,
            input_index=input_index,
            source_name=source_name,
            source_id=source_id,
            acquired_at=acquired_at,
            acquisition_mode=acquisition_mode,
            parser_version=parser_version,
            release_version=release_version,
            run_id=run_id,
        )
        provenance_records.append(provenance_record)

        target_accession, target_issue_kind, target_issue_detail = _target_reference_input(record)
        target_candidates = _target_candidates(record)
        target_id = None
        if target_issue_kind is None:
            target_id, target_issue_kind, target_issue_detail, resolved_target_candidates = (
                _protein_reference(
                    target_accession,
                    registry,
                )
            )
            if resolved_target_candidates:
                target_candidates = resolved_target_candidates
        if target_id is None:
            issues.append(
                AssayIngestIssue(
                    assay_key=assay_key,
                    kind=target_issue_kind or "target_unresolved",
                    message=_target_issue_message(
                        record,
                        target_issue_kind or "target_unresolved",
                        target_issue_detail,
                    ),
                    input_indices=(input_index,),
                    source_ids=(source_id,),
                    target_candidates=target_candidates,
                    ligand_candidates=(),
                    provenance_ids=(provenance_record.provenance_id,),
                )
            )
            continue

        ligand_candidates = _ligand_candidates(record)
        ligand_id, ligand_issue_kind, ligand_issue_detail, resolved_ligand_candidates = (
            _ligand_reference(
                _ligand_source_id(record),
                registry,
            )
        )
        if resolved_ligand_candidates:
            ligand_candidates = resolved_ligand_candidates
        if ligand_id is None:
            issues.append(
                AssayIngestIssue(
                    assay_key=assay_key,
                    kind=ligand_issue_kind or "ligand_unresolved",
                    message=_ligand_issue_message(
                        record,
                        ligand_issue_kind or "ligand_unresolved",
                        ligand_issue_detail,
                    ),
                    input_indices=(input_index,),
                    source_ids=(source_id,),
                    target_candidates=(target_id,),
                    ligand_candidates=ligand_candidates,
                    provenance_ids=(provenance_record.provenance_id,),
                )
            )
            continue

        if not _clean_text(record.affinity_type):
            issues.append(
                AssayIngestIssue(
                    assay_key=assay_key,
                    kind="missing_measurement_type",
                    message="assay rows require a measurement type to be canonicalized",
                    input_indices=(input_index,),
                    source_ids=(source_id,),
                    target_candidates=(target_id,),
                    ligand_candidates=(ligand_id,),
                    provenance_ids=(provenance_record.provenance_id,),
                )
            )
            continue

        if record.affinity_value_nM is None:
            issues.append(
                AssayIngestIssue(
                    assay_key=assay_key,
                    kind="missing_measurement_value",
                    message="assay rows without a numeric measurement value remain unresolved",
                    input_indices=(input_index,),
                    source_ids=(source_id,),
                    target_candidates=(target_id,),
                    ligand_candidates=(ligand_id,),
                    provenance_ids=(provenance_record.provenance_id,),
                )
            )
            continue

        payloads.append(
            _payload_from_record(
                record,
                source_name=source_name,
                source_id=source_id,
                target_id=target_id,
                ligand_id=ligand_id,
                provenance_id=provenance_record.provenance_id,
            )
        )

    if issues:
        return AssayIngestCase(
            assay_key=assay_key,
            status="unresolved",
            canonical_assay=None,
            provenance_records=tuple(provenance_records),
            observations=tuple(record for _, record in indexed_records),
            issues=tuple(issues),
            conflicts=(),
            alternative_values={},
            reason=issues[0].kind,
        )

    merge_result = merge_assay_records(payloads)
    if merge_result.status in {"conflict", "unresolved"}:
        return AssayIngestCase(
            assay_key=assay_key,
            status=merge_result.status,
            canonical_assay=None,
            provenance_records=tuple(provenance_records),
            observations=tuple(record for _, record in indexed_records),
            issues=(
                AssayIngestIssue(
                    assay_key=assay_key,
                    kind="assay_conflict",
                    message=merge_result.reason.replace("_", " "),
                    input_indices=tuple(input_index for input_index, _ in indexed_records),
                    source_ids=tuple(
                        source_id
                        for _, record in indexed_records
                        if (source_id := _source_id(record)) is not None
                    ),
                    target_candidates=tuple(
                        payload["target_id"] for payload in payloads
                    ),
                    ligand_candidates=tuple(
                        payload["ligand_id"] for payload in payloads
                    ),
                    provenance_ids=tuple(
                        provenance_record.provenance_id for provenance_record in provenance_records
                    ),
                    conflicts=merge_result.conflicts,
                ),
            ),
            conflicts=merge_result.conflicts,
            alternative_values=merge_result.alternative_values,
            reason=merge_result.reason,
        )

    canonical_assay = _build_canonical_assay(
        payloads=payloads,
        provenance_records=provenance_records,
        observations=tuple(record for _, record in indexed_records),
        source_name=source_name,
    )
    status: AssayIngestStatus = "resolved" if len(indexed_records) == 1 else "ambiguous"
    reason = (
        "single_assay_record_ingested"
        if len(indexed_records) == 1
        else "duplicate_evidence_preserved"
    )
    if merge_result.status == "ambiguous":
        status = "ambiguous"
        reason = merge_result.reason
    return AssayIngestCase(
        assay_key=assay_key,
        status=status,
        canonical_assay=canonical_assay,
        provenance_records=tuple(provenance_records),
        observations=tuple(record for _, record in indexed_records),
        issues=(),
        conflicts=(),
        alternative_values=merge_result.alternative_values,
        reason=reason,
    )


def _build_provenance_record(
    record: BindingDBAssayRecord,
    *,
    input_index: int,
    source_name: str,
    source_id: str,
    acquired_at: str | None,
    acquisition_mode: str,
    parser_version: str | None,
    release_version: str | None,
    run_id: str | None,
) -> ProvenanceRecord:
    raw_payload = record.raw or record.to_dict()
    checksum_source = raw_payload if isinstance(raw_payload, Mapping) else record.to_dict()
    checksum = _stable_checksum(_json_ready(checksum_source))
    source = ProvenanceSource(
        source_name=source_name,
        acquisition_mode=acquisition_mode,
        original_identifier=source_id,
        release_version=release_version,
    )
    return ProvenanceRecord(
        provenance_id=f"prov:{source_name}:{source_id}:{input_index + 1}",
        source=source,
        transformation_step="canonical_assay_ingest",
        acquired_at=acquired_at,
        parser_version=parser_version,
        transformation_history=("bindingdb_assay_parse",),
        run_id=run_id,
        confidence=None,
        checksum=checksum,
        raw_payload_pointer=f"{source_name.lower()}:{source_id}",
        metadata={
            "input_index": input_index,
            "source_id": source_id,
            "reactant_set_id": record.reactant_set_id,
            "monomer_id": record.monomer_id,
            "target_uniprot_ids": list(record.target_uniprot_ids),
            "target_pdb_ids": list(record.target_pdb_ids),
            "affinity_type": record.affinity_type,
            "affinity_value_nM": record.affinity_value_nM,
            "assay_description": record.assay_description,
            "publication_date": record.publication_date,
            "curation_date": record.curation_date,
        },
    )


def _build_canonical_assay(
    *,
    payloads: list[dict[str, Any]],
    provenance_records: list[ProvenanceRecord],
    observations: tuple[BindingDBAssayRecord, ...],
    source_name: str,
) -> CanonicalAssay:
    first_payload = payloads[0]
    return CanonicalAssay(
        assay_id=f"assay:{source_name.upper()}:{first_payload['source_id']}",
        target_id=first_payload["target_id"],
        ligand_id=first_payload["ligand_id"],
        source=source_name,
        source_id=first_payload["source_id"],
        measurement_type=first_payload["measurement_type"],
        measurement_value=first_payload["measurement_value"],
        measurement_unit=first_payload["measurement_unit"],
        relation=_consensus_text(payload["relation"] for payload in payloads),
        assay_conditions=_consensus_text(payload["assay_conditions"] for payload in payloads),
        ph=_consensus_float(payload["ph"] for payload in payloads),
        temperature_celsius=_consensus_float(
            payload["temperature_celsius"] for payload in payloads
        ),
        references=_dedupe(
            reference
            for observation in observations
            for reference in _extract_reference_strings(observation.raw)
        ),
        provenance=tuple(record.provenance_id for record in provenance_records),
    )


def _target_reference_input(
    record: BindingDBAssayRecord,
) -> tuple[str | None, AssayIngestIssueKind | None, str | None]:
    if len(record.target_uniprot_ids) == 1:
        return record.target_uniprot_ids[0], None, None
    if not record.target_uniprot_ids:
        return None, "missing_target_identifier", None
    return None, "target_ambiguity", None


def _ligand_source_id(record: BindingDBAssayRecord) -> str | None:
    return _clean_optional_text(record.monomer_id)


def _target_candidates(record: BindingDBAssayRecord) -> tuple[str, ...]:
    candidates = tuple(f"protein:{accession}" for accession in record.target_uniprot_ids)
    return candidates


def _ligand_candidates(record: BindingDBAssayRecord) -> tuple[str, ...]:
    source_id = _clean_optional_text(record.monomer_id)
    if source_id is None:
        return ()
    return (f"bindingdb:{source_id}",)


def _target_issue_message(
    record: BindingDBAssayRecord,
    kind: AssayIngestIssueKind,
    detail: str | None,
) -> str:
    if kind == "target_unresolved" and detail:
        return f"target reference could not be resolved: {detail}"
    if kind == "missing_target_identifier":
        return "BindingDB row does not supply a UniProt target accession"
    if not record.target_uniprot_ids:
        return "BindingDB row does not supply a UniProt target accession"
    return "BindingDB row supplies multiple UniProt target accessions"


def _ligand_issue_message(
    record: BindingDBAssayRecord,
    kind: AssayIngestIssueKind,
    detail: str | None,
) -> str:
    if kind == "ligand_unresolved" and detail:
        return f"ligand reference could not be resolved: {detail}"
    if kind == "missing_ligand_identifier":
        return "BindingDB row does not supply a ligand source identifier"
    if not record.monomer_id:
        return "BindingDB row does not supply a ligand source identifier"
    return "BindingDB row supplies an ambiguous ligand source identifier"


def _batch_status(cases: Iterable[AssayIngestCase]) -> AssayIngestStatus:
    case_statuses = [case.status for case in cases]
    if "conflict" in case_statuses:
        return "conflict"
    if "unresolved" in case_statuses:
        return "unresolved"
    if "ambiguous" in case_statuses:
        return "ambiguous"
    return "resolved"


def _batch_reason(status: AssayIngestStatus, cases: Iterable[AssayIngestCase]) -> str:
    if status == "resolved":
        return "all_assay_rows_ingested"
    if status == "ambiguous":
        return "one_or_more_assays_preserved_with_shared_provenance"
    if status == "conflict":
        return "one_or_more_assays_conflicted"
    return "one_or_more_assays_unresolved"


__all__ = [
    "AssayIngestCase",
    "AssayIngestIssue",
    "AssayIngestIssueKind",
    "AssayIngestResult",
    "AssayIngestStatus",
    "ingest_assay_records",
    "ingest_assays_to_canonical_layer",
    "ingest_bindingdb_assays",
    "parse_bindingdb_assay_row",
    "parse_bindingdb_assays",
]
