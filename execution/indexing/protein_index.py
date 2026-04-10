from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from core.storage.planning_index_schema import (
    PlanningIndexCoverage,
    PlanningIndexEntry,
    PlanningIndexMaterializationPointer,
    PlanningIndexSchema,
    PlanningIndexSourceRecord,
)
from execution.ingest.sequences import (
    SequenceIngestObservation,
    SequenceIngestOutcome,
    SequenceIngestResult,
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


def _unique_text(values: Iterable[Any]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _stringify_bool(value: bool | None) -> str | None:
    if value is None:
        return None
    return "true" if value else "false"


def _normalize_accession(value: Any) -> str:
    accession = _clean_text(value).upper()
    if not accession:
        raise ValueError("protein entries require a non-empty accession")
    return accession


def _source_release_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _source_release_from_observation(
    observation: SequenceIngestObservation,
    source_release: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = _source_release_payload(source_release)
    if payload:
        return payload
    metadata = observation.provenance_record.metadata
    if not isinstance(metadata, Mapping):
        return {}
    source_release_payload = metadata.get("source_release")
    return _source_release_payload(source_release_payload)


def _required_source_stamp(
    observation: SequenceIngestObservation,
    source_release: Mapping[str, Any] | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    payload = _source_release_from_observation(observation, source_release)
    release_version = _optional_text(
        payload.get("release_version")
        or payload.get("release")
        or observation.release
        or observation.provenance_record.source.release_version
    )
    release_date = _optional_text(
        payload.get("release_date")
        or payload.get("date")
        or observation.release_date
    )
    manifest_id = _optional_text(
        payload.get("manifest_id")
        or observation.provenance_record.source.snapshot_id
    )
    source_locator = _optional_text(payload.get("source_locator"))
    if release_version is None and release_date is None and manifest_id is None:
        raise ValueError("protein planning index entries require a pinned source release")
    return release_version, release_date, manifest_id, source_locator


def _source_record_id(observation: SequenceIngestObservation) -> str:
    return _clean_text(
        observation.source_id
        or observation.entry_name
        or observation.accession
        or observation.provenance_record.provenance_id
    )


def _source_keys(observation: SequenceIngestObservation) -> dict[str, str]:
    keys: dict[str, str] = {}
    for key, value in (
        ("accession", observation.accession),
        ("entry_name", observation.entry_name),
        ("source_kind", observation.source_kind),
        ("organism", observation.organism),
        ("provenance_id", observation.provenance_record.provenance_id),
        ("source_id", observation.source_id),
        ("sequence_length", observation.sequence_length),
        ("reviewed", _stringify_bool(observation.reviewed)),
    ):
        text = _optional_text(value)
        if text is not None:
            keys[key] = text
    return keys


def _build_source_record(
    observation: SequenceIngestObservation,
    *,
    source_release: Mapping[str, Any] | None,
) -> PlanningIndexSourceRecord:
    release_version, release_date, manifest_id, source_locator = _required_source_stamp(
        observation,
        source_release,
    )
    return PlanningIndexSourceRecord(
        source_name=observation.source,
        source_record_id=_source_record_id(observation),
        release_version=release_version,
        release_date=release_date,
        source_locator=source_locator,
        manifest_id=manifest_id,
        source_keys=_source_keys(observation),
    )


def _pointer_kind_for_reference(reference: str) -> str:
    lowered = reference.strip().casefold()
    suffix = lowered.rsplit(".", 1)[-1] if "." in lowered else ""
    if suffix in {"cif", "bcif", "pdb", "ent"}:
        return "coordinates"
    if suffix in {"mrc", "map", "ccp4"}:
        return "map"
    if suffix in {"msa", "a3m", "aln", "fasta", "fa"}:
        return "alignment"
    if suffix in {"tsv", "csv", "tab", "mitab"}:
        return "table"
    if suffix in {"json", "xml", "html", "htm"}:
        return "portal_payload"
    return "other"


def _lazy_pointers(
    observation: SequenceIngestObservation,
    *,
    source_release: Mapping[str, Any] | None,
) -> tuple[PlanningIndexMaterializationPointer, ...]:
    pointers: list[PlanningIndexMaterializationPointer] = []
    seen: set[tuple[str, str, str | None, str | None]] = set()

    raw_pointer = _optional_text(observation.provenance_record.raw_payload_pointer)
    if raw_pointer is not None:
        key = ("raw", raw_pointer, observation.source, _source_record_id(observation))
        seen.add(key)
        pointers.append(
            PlanningIndexMaterializationPointer(
                materialization_kind=_pointer_kind_for_reference(raw_pointer),
                pointer=raw_pointer,
                source_name=observation.source,
                source_record_id=_source_record_id(observation),
                notes=(f"provenance:{observation.provenance_record.provenance_id}",),
            )
        )

    payload = _source_release_payload(source_release)
    for ref in _iter_values(payload.get("local_artifact_refs")):
        reference = _optional_text(ref)
        if reference is None:
            continue
        key = ("artifact", reference, observation.source, _source_record_id(observation))
        if key in seen:
            continue
        seen.add(key)
        pointers.append(
            PlanningIndexMaterializationPointer(
                materialization_kind=_pointer_kind_for_reference(reference),
                pointer=reference,
                source_name=observation.source,
                source_record_id=_source_record_id(observation),
                notes=(f"manifest:{payload.get('manifest_id') or ''}".strip(": "),),
            )
        )

    return tuple(pointers)


def _join_status_for_outcome(
    outcome: SequenceIngestOutcome,
    *,
    accession: str | None,
) -> str:
    if outcome.status == "resolved":
        return "joined"
    if outcome.status == "ambiguous":
        return "ambiguous"
    if outcome.status == "conflict":
        return "conflict"
    if outcome.status == "unresolved":
        return "candidate" if accession else "unjoined"
    return "candidate" if accession else "unjoined"


def _coverage_for_outcome(
    outcome: SequenceIngestOutcome,
    *,
    source_names: tuple[str, ...],
) -> tuple[PlanningIndexCoverage, ...]:
    coverage: list[PlanningIndexCoverage] = []
    for source_name in source_names:
        coverage.append(
            PlanningIndexCoverage(
                coverage_kind="source",
                label=source_name,
                coverage_state="present",
                source_names=(source_name,),
                notes=(f"source_records:{len(outcome.observations)}",),
            )
        )

    sequence_state = "unknown"
    if outcome.canonical_protein is not None:
        sequence_state = "present"
    elif any(observation.sequence for observation in outcome.observations):
        sequence_state = "partial"

    coverage.append(
        PlanningIndexCoverage(
            coverage_kind="modality",
            label="protein_sequence",
            coverage_state=sequence_state,
            source_names=source_names,
            notes=(
                f"sequence_length:{outcome.canonical_protein.sequence_length}"
                if outcome.canonical_protein is not None
                else "",
            ),
        )
    )
    return tuple(coverage)


def _entry_metadata(
    outcome: SequenceIngestOutcome,
    *,
    source_release: Mapping[str, Any] | None,
    source_names: tuple[str, ...],
    source_record_ids: tuple[str, ...],
    source_provenance_ids: tuple[str, ...],
) -> dict[str, Any]:
    canonical = outcome.canonical_protein
    first_observation = outcome.observations[0]
    payload: dict[str, Any] = {
        "source_release": _source_release_payload(source_release),
        "source_names": list(source_names),
        "source_record_ids": list(source_record_ids),
        "source_provenance_ids": list(source_provenance_ids),
        "observation_count": len(outcome.observations),
        "join_reason": outcome.reason,
        "unresolved_reason": (
            outcome.unresolved_reference.reason
            if outcome.unresolved_reference is not None
            else None
        ),
        "sequence_length": (
            canonical.sequence_length
            if canonical is not None
            else first_observation.sequence_length
        ),
        "organism": first_observation.organism or None,
        "reviewed": first_observation.reviewed,
        "source_kind": first_observation.source_kind or None,
    }
    if canonical is not None:
        payload["canonical_id"] = canonical.canonical_id
        payload["accession"] = canonical.accession
    return payload


def _entry_from_outcome(
    outcome: SequenceIngestOutcome,
    *,
    source_release: Mapping[str, Any] | None = None,
) -> PlanningIndexEntry | None:
    if not outcome.observations:
        return None

    accession = _optional_text(outcome.accession)
    canonical = outcome.canonical_protein
    if accession is None and canonical is None:
        return None
    if accession is None and canonical is not None:
        accession = canonical.accession
    if accession is None:
        return None

    source_release_payload = source_release
    if source_release_payload is None:
        source_release_payload = _source_release_from_observation(
            outcome.observations[0],
            None,
        )

    source_records: list[PlanningIndexSourceRecord] = []
    seen_source_records: set[tuple[str, str]] = set()
    for observation in outcome.observations:
        source_record = _build_source_record(
            observation,
            source_release=source_release_payload,
        )
        key = (source_record.source_name.casefold(), source_record.source_record_id.casefold())
        if key in seen_source_records:
            continue
        seen_source_records.add(key)
        source_records.append(source_record)

    if not source_records:
        return None

    source_names = _unique_text(record.source_name for record in source_records)
    source_record_ids = tuple(record.source_record_id for record in source_records)
    source_provenance_ids = tuple(
        _unique_text(
            observation.provenance_record.provenance_id
            for observation in outcome.observations
        )
    )
    canonical_id = canonical.canonical_id if canonical is not None else None

    return PlanningIndexEntry(
        planning_id=f"protein:{_normalize_accession(accession)}",
        source_records=tuple(source_records),
        canonical_ids=(canonical_id,) if canonical_id is not None else (),
        join_status=_join_status_for_outcome(outcome, accession=accession),
        join_confidence=None,
        coverage=_coverage_for_outcome(outcome, source_names=source_names),
        lazy_materialization_pointers=tuple(
            pointer
            for observation in outcome.observations
            for pointer in _lazy_pointers(
                observation,
                source_release=source_release_payload,
            )
        ),
        metadata=_entry_metadata(
            outcome,
            source_release=source_release_payload,
            source_names=source_names,
            source_record_ids=source_record_ids,
            source_provenance_ids=source_provenance_ids,
        ),
    )


def _iter_outcomes(records: object) -> tuple[SequenceIngestOutcome, ...]:
    if isinstance(records, SequenceIngestResult):
        return records.outcomes
    if isinstance(records, SequenceIngestOutcome):
        return (records,)
    if isinstance(records, Iterable) and not isinstance(records, (str, bytes, Mapping)):
        outcomes: list[SequenceIngestOutcome] = []
        for record in records:
            if not isinstance(record, SequenceIngestOutcome):
                raise TypeError("records must contain SequenceIngestOutcome instances")
            outcomes.append(record)
        return tuple(outcomes)
    raise TypeError("records must be a SequenceIngestResult or iterable of outcomes")


def build_protein_planning_index(
    records: object,
    *,
    schema_version: int = 1,
) -> PlanningIndexSchema:
    """Build a conservative protein planning index from join outputs."""

    if isinstance(records, PlanningIndexSchema):
        return records

    outcomes = _iter_outcomes(records)
    source_release = (
        records.source_release if isinstance(records, SequenceIngestResult) else None
    )
    entries = [
        entry
        for outcome in outcomes
        if (entry := _entry_from_outcome(
            outcome,
            source_release=source_release,
        ))
        is not None
    ]
    entries.sort(key=lambda entry: entry.planning_id.casefold())
    return PlanningIndexSchema(records=tuple(entries), schema_version=schema_version)


__all__ = ["build_protein_planning_index"]
