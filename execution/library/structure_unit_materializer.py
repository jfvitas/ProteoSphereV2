from __future__ import annotations

from collections.abc import Iterable

from core.library.summary_record import (
    ProteinSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryLibrarySchema,
    SummaryRecordContext,
    SummaryReference,
)


def _note_lookup(notes: Iterable[str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for note in notes:
        text = str(note or "").strip()
        if not text or ":" not in text:
            continue
        key, value = text.split(":", 1)
        key = key.strip().casefold()
        value = value.strip()
        if key and value:
            lookup.setdefault(key, value)
    return lookup


def _structure_refs(record: ProteinSummaryRecord) -> tuple[SummaryReference, ...]:
    return tuple(
        reference
        for reference in record.context.domain_references
        if reference.namespace in {"CATH", "SCOPe"}
    )


def materialize_structure_unit_records(
    library: SummaryLibrarySchema | Iterable[ProteinSummaryRecord],
) -> tuple[StructureUnitSummaryRecord, ...]:
    protein_records = (
        library.protein_records
        if isinstance(library, SummaryLibrarySchema)
        else tuple(library)
    )
    grouped: dict[
        tuple[str, str, str],
        dict[str, object],
    ] = {}

    for record in protein_records:
        for reference in _structure_refs(record):
            note_map = _note_lookup(reference.notes)
            pdb_id = note_map.get("pdb_id", "").upper()
            chain_id = note_map.get("chain", "").upper()
            if not pdb_id or not chain_id:
                continue
            key = (record.protein_ref, pdb_id, chain_id)
            bucket = grouped.setdefault(
                key,
                {
                    "protein_record": record,
                    "references": [],
                    "span_start": [],
                    "span_end": [],
                    "relation_notes": [],
                },
            )
            bucket["references"].append(reference)
            if reference.span_start is not None:
                bucket["span_start"].append(reference.span_start)
            if reference.span_end is not None:
                bucket["span_end"].append(reference.span_end)
            if reference.source_record_id:
                bucket["relation_notes"].append(
                    f"{reference.namespace.lower()}_source_record_id:{reference.source_record_id}"
                )
            bucket["relation_notes"].append(f"structure_chain:{pdb_id}:{chain_id}")

    structure_units: list[StructureUnitSummaryRecord] = []
    for (protein_ref, pdb_id, chain_id), bucket in sorted(grouped.items()):
        protein_record = bucket["protein_record"]
        references = tuple(bucket["references"])
        span_start_values = bucket["span_start"]
        span_end_values = bucket["span_end"]
        relation_notes = tuple(dict.fromkeys(bucket["relation_notes"]))
        structure_units.append(
            StructureUnitSummaryRecord(
                summary_id=f"structure_unit:{protein_ref}:{pdb_id}:{chain_id}",
                protein_ref=protein_ref,
                structure_source="PDB",
                structure_id=pdb_id,
                structure_kind="classification_anchored_chain",
                chain_id=chain_id,
                residue_span_start=min(span_start_values) if span_start_values else None,
                residue_span_end=max(span_end_values) if span_end_values else None,
                experimental_or_predicted="experimental",
                mapping_status="joined",
                structure_relation_notes=relation_notes,
                context=SummaryRecordContext(
                    provenance_pointers=protein_record.context.provenance_pointers,
                    domain_references=references,
                    source_connections=tuple(
                        connection
                        for connection in protein_record.context.source_connections
                        if connection.connection_kind == "structure"
                        and any(
                            f"PDB:{pdb_id}" == bridge_id.upper()
                            or f"CHAIN:{chain_id}" == bridge_id.upper()
                            for bridge_id in connection.bridge_ids
                        )
                    ),
                    storage_notes=(
                        "first executable structure-unit slice derived from "
                        "protein summary classification joins",
                    ),
                ),
                notes=(
                    f"source_protein_summary_id:{protein_record.summary_id}",
                    f"classification_reference_count:{len(references)}",
                ),
            )
        )
    return tuple(structure_units)


def build_structure_unit_summary_library(
    library: SummaryLibrarySchema | Iterable[ProteinSummaryRecord],
    *,
    library_id: str = "summary-library:structure-units:v1",
    source_manifest_id: str | None = None,
    schema_version: int = 2,
) -> SummaryLibrarySchema:
    structure_units = materialize_structure_unit_records(library)
    if isinstance(library, SummaryLibrarySchema):
        manifest_id = source_manifest_id or library.source_manifest_id
    else:
        manifest_id = source_manifest_id
    return SummaryLibrarySchema(
        library_id=library_id,
        records=structure_units,
        schema_version=schema_version,
        source_manifest_id=manifest_id,
        index_guidance=(
            "route structure units by protein_ref, structure_id, and chain_id",
            "keep experimental structure chain lineage visible for similarity and leakage control",
        ),
        storage_guidance=(
            "treat structure-unit summaries as a rebuildable feature-cache layer",
            "defer coordinate-heavy structure hydration until packet selection",
        ),
        lazy_loading_guidance=(
            "reuse protein-level classification joins as the first executable structure-unit seed",
        ),
    )


__all__ = [
    "build_structure_unit_summary_library",
    "materialize_structure_unit_records",
]
