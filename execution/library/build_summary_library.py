from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from core.library.summary_record import (
    ProteinLigandSummaryRecord,
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    ProteinVariantSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryLibrarySchema,
    SummaryRecord,
)
from execution.indexing.protein_pair_crossref import (
    ProteinPairCrossReferenceIndex,
    ProteinPairCrossReferenceRecord,
)

DEFAULT_SUMMARY_LIBRARY_INDEX_GUIDANCE = (
    "route protein, pair, and ligand summaries accession-first",
    "keep unresolved pair references visible instead of collapsing them",
    "preserve source evidence and provenance alongside canonical ids",
)
DEFAULT_SUMMARY_LIBRARY_STORAGE_GUIDANCE = (
    "treat the summary library as a rebuildable feature-cache layer",
    "preserve pinned source-backed records and canonical ids separately",
    "defer heavy coordinates, maps, alignments, and portal payloads until selection",
)
DEFAULT_SUMMARY_LIBRARY_LAZY_GUIDANCE = (
    "hydrate heavy source payloads only after selection",
    "keep pair provenance, source evidence, and unresolved gaps attached to the record",
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


def _merge_guidance(*groups: Iterable[Any]) -> tuple[str, ...]:
    return _unique_text(item for group in groups for item in _iter_values(group))


def _unresolved_note(reference: Any) -> str:
    if hasattr(reference, "to_dict") and callable(reference.to_dict):
        payload = reference.to_dict()
    elif isinstance(reference, Mapping):
        payload = dict(reference)
    else:
        payload = {
            "reference": getattr(reference, "reference", ""),
            "entity_type": getattr(reference, "entity_type", None),
            "reason": getattr(reference, "reason", "missing"),
            "candidates": getattr(reference, "candidates", ()),
        }

    ref = _clean_text(payload.get("reference"))
    entity_type = _optional_text(payload.get("entity_type")) or "any"
    reason = _optional_text(payload.get("reason")) or "missing"
    candidates = _unique_text(_iter_values(payload.get("candidates")))
    note = f"unresolved_reference:{entity_type}:{ref}:{reason}"
    if candidates:
        note = f"{note}:{'|'.join(candidates)}"
    return note


def _pair_summary_record(record: ProteinPairCrossReferenceRecord) -> SummaryRecord:
    unresolved_notes = tuple(
        _unresolved_note(reference) for reference in record.unresolved_references
    )
    if record.record_type == "protein_protein":
        protein_a_ref = (
            record.canonical_protein_ids[0]
            if record.canonical_protein_ids
            else record.protein_refs[0]
        )
        protein_b_ref = (
            record.canonical_protein_ids[1]
            if len(record.canonical_protein_ids) > 1
            else record.protein_refs[1]
        )
        return ProteinProteinSummaryRecord(
            summary_id=record.summary_id,
            protein_a_ref=protein_a_ref,
            protein_b_ref=protein_b_ref,
            interaction_refs=record.source_evidence_refs,
            evidence_refs=record.source_record_ids,
            join_status=record.join_status,
            join_reason=record.join_reason,
            context=record.context,
            notes=unresolved_notes,
        )

    protein_ref = (
        record.canonical_protein_ids[0]
        if record.canonical_protein_ids
        else record.protein_refs[0]
    )
    ligand_ref = (
        record.canonical_ligand_ids[0]
        if record.canonical_ligand_ids
        else record.ligand_refs[0]
    )
    return ProteinLigandSummaryRecord(
        summary_id=record.summary_id,
        protein_ref=protein_ref,
        ligand_ref=ligand_ref,
        interaction_refs=record.source_evidence_refs,
        assay_refs=record.source_record_ids,
        join_status=record.join_status,
        join_reason=record.join_reason,
        context=record.context,
        notes=unresolved_notes,
    )


def _summary_record_from_mapping(payload: Mapping[str, Any]) -> SummaryRecord:
    record_type = _clean_text(payload.get("record_type") or payload.get("type")).casefold()
    if (
        "protein_refs" in payload
        or "canonical_protein_ids" in payload
        or "source_evidence_refs" in payload
        or "unresolved_references" in payload
    ):
        return _pair_summary_record(ProteinPairCrossReferenceRecord.from_dict(payload))
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
    if "protein_a_ref" in payload and "protein_b_ref" in payload:
        return ProteinProteinSummaryRecord.from_dict(payload)
    if "protein_ref" in payload and "ligand_ref" in payload:
        return ProteinLigandSummaryRecord.from_dict(payload)
    raise ValueError("unable to determine summary record type")


def _coerce_summary_record(value: Any) -> SummaryRecord:
    if isinstance(
        value,
        (
            ProteinSummaryRecord,
            ProteinVariantSummaryRecord,
            StructureUnitSummaryRecord,
            ProteinProteinSummaryRecord,
            ProteinLigandSummaryRecord,
        ),
    ):
        return value
    if isinstance(value, ProteinPairCrossReferenceRecord):
        return _pair_summary_record(value)
    if isinstance(value, Mapping):
        return _summary_record_from_mapping(value)
    raise TypeError("records must contain summary record objects or mappings")


def _coerce_summary_records(records: object) -> tuple[SummaryRecord, ...]:
    if isinstance(records, SummaryLibrarySchema):
        return tuple(records.records)
    if isinstance(records, Mapping):
        if "record_type" in records or "type" in records:
            return (_coerce_summary_record(records),)
        if "records" in records or "summary_records" in records:
            try:
                library = SummaryLibrarySchema.from_dict(records)
            except Exception as exc:
                raise TypeError(
                    "records must be a summary library schema or iterable of summary records"
                ) from exc
            return tuple(library.records)
        raise TypeError("records must be a summary library schema or iterable of summary records")
    if isinstance(records, Iterable) and not isinstance(records, (str, bytes)):
        return tuple(_coerce_summary_record(item) for item in records)
    return (_coerce_summary_record(records),)


def _coerce_crossref_index(
    value: ProteinPairCrossReferenceIndex | Mapping[str, Any] | None,
) -> ProteinPairCrossReferenceIndex | None:
    if value is None:
        return None
    if isinstance(value, ProteinPairCrossReferenceIndex):
        return value
    if isinstance(value, Mapping):
        return ProteinPairCrossReferenceIndex.from_dict(value)
    raise TypeError(
        "pair_crossref_index must be a ProteinPairCrossReferenceIndex, mapping, or None"
    )


def _dedupe_summary_records(records: Iterable[SummaryRecord]) -> tuple[SummaryRecord, ...]:
    ordered: dict[str, SummaryRecord] = {}
    for record in records:
        ordered[record.summary_id.casefold()] = record
    return tuple(sorted(ordered.values(), key=lambda record: record.summary_id.casefold()))


def build_summary_library(
    records: object,
    *,
    pair_crossref_index: ProteinPairCrossReferenceIndex | Mapping[str, Any] | None = None,
    library_id: str = "summary-library",
    source_manifest_id: str | None = None,
    schema_version: int = 1,
    index_guidance: Iterable[str] = (),
    storage_guidance: Iterable[str] = (),
    lazy_loading_guidance: Iterable[str] = (),
) -> SummaryLibrarySchema:
    if isinstance(records, SummaryLibrarySchema):
        if (
            pair_crossref_index is None
            and source_manifest_id is None
            and schema_version == records.schema_version
            and not _iter_values(index_guidance)
            and not _iter_values(storage_guidance)
            and not _iter_values(lazy_loading_guidance)
        ):
            return records
        base_records = tuple(records.records)
        base_library_id = records.library_id
        base_source_manifest_id = records.source_manifest_id
        base_index_guidance = records.index_guidance
        base_storage_guidance = records.storage_guidance
        base_lazy_guidance = records.lazy_loading_guidance
    elif isinstance(records, Mapping) and ("records" in records or "summary_records" in records):
        library = SummaryLibrarySchema.from_dict(records)
        if (
            pair_crossref_index is None
            and source_manifest_id is None
            and schema_version == library.schema_version
            and not _iter_values(index_guidance)
            and not _iter_values(storage_guidance)
            and not _iter_values(lazy_loading_guidance)
        ):
            return library
        base_records = tuple(library.records)
        base_library_id = library.library_id
        base_source_manifest_id = library.source_manifest_id
        base_index_guidance = library.index_guidance
        base_storage_guidance = library.storage_guidance
        base_lazy_guidance = library.lazy_loading_guidance
    else:
        base_records = _coerce_summary_records(records)
        base_library_id = _optional_text(library_id) or "summary-library"
        base_source_manifest_id = None
        base_index_guidance = ()
        base_storage_guidance = ()
        base_lazy_guidance = ()

    crossref_index = _coerce_crossref_index(pair_crossref_index)
    records_to_materialize = list(base_records)
    if crossref_index is not None:
        records_to_materialize.extend(
            _pair_summary_record(record) for record in crossref_index.records
        )
        if base_source_manifest_id is None:
            base_source_manifest_id = crossref_index.source_manifest_id
        base_index_guidance = _merge_guidance(base_index_guidance, crossref_index.index_guidance)
        base_storage_guidance = _merge_guidance(
            base_storage_guidance,
            crossref_index.storage_guidance,
        )
        base_lazy_guidance = _merge_guidance(
            base_lazy_guidance,
            crossref_index.lazy_loading_guidance,
        )

    if source_manifest_id is not None:
        base_source_manifest_id = _optional_text(source_manifest_id)

    merged_records = _dedupe_summary_records(records_to_materialize)
    merged_index_guidance = _merge_guidance(
        DEFAULT_SUMMARY_LIBRARY_INDEX_GUIDANCE,
        base_index_guidance,
        index_guidance,
    )
    merged_storage_guidance = _merge_guidance(
        DEFAULT_SUMMARY_LIBRARY_STORAGE_GUIDANCE,
        base_storage_guidance,
        storage_guidance,
    )
    merged_lazy_guidance = _merge_guidance(
        DEFAULT_SUMMARY_LIBRARY_LAZY_GUIDANCE,
        base_lazy_guidance,
        lazy_loading_guidance,
    )

    return SummaryLibrarySchema(
        library_id=base_library_id,
        records=merged_records,
        schema_version=schema_version,
        source_manifest_id=base_source_manifest_id,
        index_guidance=merged_index_guidance,
        storage_guidance=merged_storage_guidance,
        lazy_loading_guidance=merged_lazy_guidance,
    )


__all__ = [
    "DEFAULT_SUMMARY_LIBRARY_INDEX_GUIDANCE",
    "DEFAULT_SUMMARY_LIBRARY_LAZY_GUIDANCE",
    "DEFAULT_SUMMARY_LIBRARY_STORAGE_GUIDANCE",
    "build_summary_library",
]
