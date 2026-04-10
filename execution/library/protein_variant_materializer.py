from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import replace
from pathlib import Path

from core.library.summary_record import (
    ProteinSummaryRecord,
    ProteinVariantSummaryRecord,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTEIN_SUMMARY_LIBRARY_PATH = (
    ROOT / "artifacts" / "status" / "protein_summary_library.json"
)
DEFAULT_UNIPROT_ROOT = ROOT / "data" / "raw" / "uniprot"
DEFAULT_INTACT_MUTATION_PATH = (
    ROOT / "data" / "raw" / "protein_data_scope_seed" / "intact" / "mutation.tsv"
)
DEFAULT_VARIANT_EVIDENCE_PATHS = (
    ROOT / "artifacts" / "status" / "p54_variant_evidence_hunt.json",
    ROOT / "artifacts" / "status" / "p58_globin_variant_evidence_hunt.json",
)
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "status" / "protein_variant_summary_library.json"
DEFAULT_LIBRARY_ID = "summary-library:protein-variants:v1"
UNIPROT_RELEASE_VERSION = "2026-03-23"
INTACT_RELEASE_VERSION = "20260323T002625Z"
INTACT_MAX_PROVENANCE_POINTERS = 5
_RANGE_PATTERN = re.compile(r"^\s*(?P<start>\d+)\s*-\s*(?P<end>\d+)\s*$")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _accession_from_protein_ref(protein_ref: str) -> str:
    return _clean_text(protein_ref).split(":")[-1]


def _parse_position(value: object) -> int | None:
    if not isinstance(value, Mapping):
        return None
    raw = _clean_text(value.get("value"))
    if not raw or _clean_text(value.get("modifier")).upper() != "EXACT":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_location(location: object) -> tuple[int | None, int | None]:
    if not isinstance(location, Mapping):
        return None, None
    return _parse_position(location.get("start")), _parse_position(location.get("end"))


def _mutation_sort_key(token: str) -> tuple[int, str]:
    match = re.search(r"(\d+)", token)
    return (int(match.group(1)) if match else 10**9, token)


def _dedupe_text(values: Iterable[object]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _dedupe_provenance(
    pointers: Iterable[SummaryProvenancePointer],
) -> tuple[SummaryProvenancePointer, ...]:
    ordered: dict[
        tuple[str, str | None, str | None, str | None],
        SummaryProvenancePointer,
    ] = {}
    for pointer in pointers:
        key = (
            pointer.source_name.casefold(),
            pointer.source_record_id.casefold() if pointer.source_record_id else None,
            pointer.release_version,
            pointer.provenance_id,
        )
        ordered.setdefault(key, pointer)
    return tuple(ordered.values())


def _supported_accessions(paths: Iterable[Path | None]) -> tuple[str, ...]:
    values: list[str] = []
    for path in paths:
        if path is None or not path.exists():
            continue
        payload = _read_json(path)
        support_scope = payload.get("support_scope")
        if not isinstance(support_scope, Mapping):
            continue
        accessions = support_scope.get("supported_accessions")
        if not isinstance(accessions, Iterable):
            continue
        values.extend(str(item) for item in accessions)
    return _dedupe_text(values)


def _load_protein_library(path: Path) -> SummaryLibrarySchema:
    payload = _read_json(path)
    return SummaryLibrarySchema.from_dict(payload)


def _load_uniprot_payload(root: Path, accession: str) -> dict[str, object] | None:
    direct_path = root / accession / f"{accession}.json"
    if direct_path.exists():
        return _read_json(direct_path)

    candidate_paths = sorted(
        (
            path
            for path in root.glob(f"*/{accession}/{accession}.json")
            if path.is_file()
        ),
        reverse=True,
    )
    if not candidate_paths:
        return None
    return _read_json(candidate_paths[0])


def _mutation_token(position: int | None, original: str, alternate: str) -> str | None:
    if position is None:
        return None
    original_text = _clean_text(original)
    alternate_text = _clean_text(alternate)
    if not original_text or not alternate_text:
        return None
    return f"{original_text}{position}{alternate_text}"


def _mutation_kind(mutations: Iterable[str]) -> str:
    tokens = tuple(_clean_text(item) for item in mutations if _clean_text(item))
    if not tokens:
        return ""
    if any("del" in token.casefold() or "ins" in token.casefold() for token in tokens):
        return "small_indel"
    if any(len(re.sub(r"\d+", "", token)) != 2 for token in tokens):
        return "small_indel"
    return "point_mutation"


def _sequence_delta_signature(mutations: Iterable[str]) -> str | None:
    values = sorted(
        {_clean_text(item) for item in mutations if _clean_text(item)},
        key=_mutation_sort_key,
    )
    if not values:
        return None
    return ";".join(values)


def _intact_delta_from_row(row: Mapping[str, str]) -> str | None:
    range_text = _clean_text(row.get("Feature range(s)"))
    match = _RANGE_PATTERN.match(range_text)
    if not match:
        return None
    start = int(match.group("start"))
    end = int(match.group("end"))
    original = _clean_text(row.get("Original sequence"))
    resulting = _clean_text(row.get("Resulting sequence"))
    if not original and not resulting:
        return None
    if start == end:
        return _mutation_token(start, original, resulting)
    return f"{original}{start}-{end}{resulting}"


def _compact_description(text: str) -> str:
    return " ".join(_clean_text(text).split())


def _record_summary_id(protein_ref: str, variant_signature: str) -> str:
    return f"protein_variant:{protein_ref}:{variant_signature}"


def _provenance_pointer(
    *,
    provenance_id: str,
    source_name: str,
    source_record_id: str | None,
    release_version: str | None,
    notes: Iterable[object],
) -> SummaryProvenancePointer:
    return SummaryProvenancePointer(
        provenance_id=provenance_id,
        source_name=source_name,
        source_record_id=source_record_id,
        release_version=release_version,
        join_status="joined",
        notes=_dedupe_text(notes),
    )


def _build_uniprot_variant_records(
    protein_record: ProteinSummaryRecord,
    accession: str,
    payload: Mapping[str, object],
) -> tuple[ProteinVariantSummaryRecord, ...]:
    records: list[ProteinVariantSummaryRecord] = []
    organism_name = protein_record.organism_name
    taxon_id = protein_record.taxon_id
    for feature in payload.get("features", ()):
        if not isinstance(feature, Mapping):
            continue
        feature_type = _clean_text(feature.get("type"))
        feature_id = _clean_text(feature.get("featureId"))
        start, end = _parse_location(feature.get("location"))
        description = _compact_description(_clean_text(feature.get("description")))
        alternative = feature.get("alternativeSequence")
        if not isinstance(alternative, Mapping):
            alternative = {}
        original_sequence = _clean_text(alternative.get("originalSequence"))
        alternative_sequences = tuple(
            _clean_text(item)
            for item in alternative.get("alternativeSequences", ())
            if _clean_text(item)
        )
        evidence_ids = tuple(
            _clean_text(item.get("id"))
            for item in feature.get("evidences", ())
            if isinstance(item, Mapping) and _clean_text(item.get("id"))
        )
        base_notes = [
            f"source_kind:uniprot_{feature_type.lower().replace(' ', '_')}",
            f"feature_id:{feature_id}" if feature_id else "",
            f"range:{start}-{end}" if start is not None and end is not None else "",
            f"description:{description}" if description else "",
            *(f"pubmed:{item}" for item in evidence_ids),
        ]
        if feature_type == "Natural variant":
            for alt in alternative_sequences:
                mutation = _mutation_token(start, original_sequence, alt)
                if not mutation:
                    continue
                variant_signature = mutation
                records.append(
                    ProteinVariantSummaryRecord(
                        summary_id=_record_summary_id(
                            protein_record.protein_ref,
                            variant_signature,
                        ),
                        protein_ref=protein_record.protein_ref,
                        parent_protein_ref=protein_record.protein_ref,
                        variant_signature=variant_signature,
                        variant_kind=_mutation_kind((mutation,)) or "natural_variant",
                        mutation_list=(mutation,),
                        sequence_delta_signature=mutation,
                        construct_type=None,
                        is_partial=False,
                        organism_name=organism_name,
                        taxon_id=taxon_id,
                        variant_relation_notes=_dedupe_text(base_notes),
                        join_status="joined",
                        join_reason="uniprot_variant_feature",
                        context=SummaryRecordContext(
                            provenance_pointers=(
                                _provenance_pointer(
                                    provenance_id=(
                                        f"uniprot-variant:{accession}:"
                                        f"{feature_id or variant_signature}"
                                    ),
                                    source_name="UniProt",
                                    source_record_id=feature_id or variant_signature,
                                    release_version=UNIPROT_RELEASE_VERSION,
                                    notes=(
                                        "variant_feature",
                                        f"accession:{accession}",
                                        f"variant_signature:{variant_signature}",
                                    ),
                                ),
                            ),
                            storage_notes=(
                                "first executable protein-variant slice from local "
                                "UniProt",
                            ),
                        ),
                        notes=(
                            f"source_accession:{accession}",
                            f"source_feature_type:{feature_type}",
                        ),
                    )
                )
        elif feature_type == "Alternative sequence":
            if start is None or end is None:
                continue
            feature_key = feature_id or f"{start}-{end}"
            variant_signature = f"isoform:{feature_key}:{start}-{end}"
            delta_signature = None
            partial = True
            if original_sequence and len(alternative_sequences) == 1:
                delta_signature = f"{original_sequence}{start}-{end}{alternative_sequences[0]}"
                partial = False
            elif original_sequence and alternative_sequences:
                delta_signature = ";".join(
                    f"{original_sequence}{start}-{end}{alt}" for alt in alternative_sequences
                )
            records.append(
                ProteinVariantSummaryRecord(
                    summary_id=_record_summary_id(protein_record.protein_ref, variant_signature),
                    protein_ref=protein_record.protein_ref,
                    parent_protein_ref=protein_record.protein_ref,
                    variant_signature=variant_signature,
                    variant_kind="isoform_variant",
                    mutation_list=(),
                    sequence_delta_signature=delta_signature,
                    construct_type=None,
                    is_partial=partial,
                    organism_name=organism_name,
                    taxon_id=taxon_id,
                    variant_relation_notes=_dedupe_text(base_notes),
                    join_status="partial" if partial else "joined",
                    join_reason="uniprot_isoform_feature",
                    context=SummaryRecordContext(
                        provenance_pointers=(
                            _provenance_pointer(
                                provenance_id=f"uniprot-isoform:{accession}:{feature_key}",
                                source_name="UniProt",
                                source_record_id=feature_id or feature_key,
                                release_version=UNIPROT_RELEASE_VERSION,
                                notes=(
                                    "variant_feature",
                                    f"accession:{accession}",
                                    f"variant_signature:{variant_signature}",
                                ),
                            ),
                        ),
                        storage_notes=(
                            "first executable protein-variant slice from local UniProt",
                        ),
                    ),
                    notes=(
                        f"source_accession:{accession}",
                        f"source_feature_type:{feature_type}",
                    ),
                )
            )
    return tuple(records)


def _group_intact_mutation_rows(
    mutation_path: Path,
    supported_accessions: Iterable[str],
) -> dict[str, dict[str, dict[str, object]]]:
    supported_lookup = {item.casefold() for item in supported_accessions}
    grouped: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    if not mutation_path.exists():
        return grouped
    with mutation_path.open("r", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            accession_field = _clean_text(row.get("Affected protein AC"))
            if not accession_field:
                continue
            accession = accession_field.split(":")[-1].upper()
            if accession.casefold() not in supported_lookup:
                continue
            mutation = _intact_delta_from_row(row)
            if not mutation:
                continue
            label = _clean_text(row.get("Feature short label")) or mutation
            bucket = grouped[accession].setdefault(
                label,
                {
                    "accession": accession,
                    "label": label,
                    "mutations": set(),
                    "interaction_ids": set(),
                    "pubmed_ids": set(),
                    "feature_types": set(),
                },
            )
            bucket["mutations"].add(mutation)
            interaction_id = _clean_text(row.get("Interaction AC"))
            if interaction_id:
                bucket["interaction_ids"].add(interaction_id)
            pubmed_id = _clean_text(row.get("PubMedID"))
            if pubmed_id:
                bucket["pubmed_ids"].add(pubmed_id)
            feature_type = _clean_text(row.get("Feature type"))
            if feature_type:
                bucket["feature_types"].add(feature_type)
    return grouped


def _merge_variant_records(
    existing: ProteinVariantSummaryRecord,
    *,
    provenance_pointers: Iterable[SummaryProvenancePointer],
    relation_notes: Iterable[object],
    notes: Iterable[object],
    join_reason: str,
) -> ProteinVariantSummaryRecord:
    return replace(
        existing,
        join_reason=join_reason,
        variant_relation_notes=_dedupe_text(
            existing.variant_relation_notes + tuple(relation_notes)
        ),
        context=replace(
            existing.context,
            provenance_pointers=_dedupe_provenance(
                existing.context.provenance_pointers + tuple(provenance_pointers)
            ),
            storage_notes=_dedupe_text(existing.context.storage_notes),
        ),
        notes=_dedupe_text(existing.notes + tuple(notes)),
    )


def materialize_protein_variant_records(
    protein_library: SummaryLibrarySchema | Iterable[ProteinSummaryRecord],
    *,
    uniprot_root: Path = DEFAULT_UNIPROT_ROOT,
    intact_mutation_path: Path = DEFAULT_INTACT_MUTATION_PATH,
    supported_accessions: Iterable[str] = (),
) -> tuple[ProteinVariantSummaryRecord, ...]:
    protein_records = (
        protein_library.protein_records
        if isinstance(protein_library, SummaryLibrarySchema)
        else tuple(protein_library)
    )
    protein_by_accession = {
        _accession_from_protein_ref(record.protein_ref): record for record in protein_records
    }
    allowed_accessions = tuple(
        accession
        for accession in _dedupe_text(supported_accessions)
        if accession in protein_by_accession
    )

    records_by_key: dict[tuple[str, str], ProteinVariantSummaryRecord] = {}

    for accession in allowed_accessions:
        payload = _load_uniprot_payload(uniprot_root, accession)
        if payload is None:
            continue
        protein_record = protein_by_accession[accession]
        for record in _build_uniprot_variant_records(protein_record, accession, payload):
            records_by_key[(accession, record.variant_signature)] = record

    intact_groups = _group_intact_mutation_rows(intact_mutation_path, allowed_accessions)
    for accession, groups in intact_groups.items():
        protein_record = protein_by_accession[accession]
        for group in groups.values():
            mutation_list = tuple(
                sorted(
                    {
                        _clean_text(item)
                        for item in group.get("mutations", set())
                        if _clean_text(item)
                    },
                    key=_mutation_sort_key,
                )
            )
            if not mutation_list:
                continue
            variant_signature = ";".join(mutation_list)
            provenance_pointers = tuple(
                _provenance_pointer(
                    provenance_id=f"intact-mutation:{accession}:{interaction_id}",
                    source_name="IntAct",
                    source_record_id=interaction_id,
                    release_version=INTACT_RELEASE_VERSION,
                    notes=(
                        "mutation_export",
                        f"accession:{accession}",
                        f"label:{group['label']}",
                    ),
                )
                for interaction_id in sorted(group.get("interaction_ids", set()))[
                    :INTACT_MAX_PROVENANCE_POINTERS
                ]
            )
            relation_notes = (
                "source_kind:intact_mutation_export",
                f"feature_label:{group['label']}",
                f"interaction_count:{len(group.get('interaction_ids', set()))}",
                f"pubmed_count:{len(group.get('pubmed_ids', set()))}",
                *(f"pubmed:{item}" for item in sorted(group.get("pubmed_ids", set()))[:5]),
            )
            notes = (
                f"source_accession:{accession}",
                f"source_feature_label:{group['label']}",
            )
            key = (accession, variant_signature)
            if key in records_by_key:
                records_by_key[key] = _merge_variant_records(
                    records_by_key[key],
                    provenance_pointers=provenance_pointers,
                    relation_notes=relation_notes,
                    notes=notes,
                    join_reason="uniprot_plus_intact_variant",
                )
                continue
            record = ProteinVariantSummaryRecord(
                summary_id=_record_summary_id(protein_record.protein_ref, variant_signature),
                protein_ref=protein_record.protein_ref,
                parent_protein_ref=protein_record.protein_ref,
                variant_signature=variant_signature,
                variant_kind=_mutation_kind(mutation_list),
                mutation_list=mutation_list,
                sequence_delta_signature=_sequence_delta_signature(mutation_list),
                construct_type=None,
                is_partial=False,
                organism_name=protein_record.organism_name,
                taxon_id=protein_record.taxon_id,
                variant_relation_notes=_dedupe_text(relation_notes),
                join_status="joined",
                join_reason="intact_mutation_export",
                context=SummaryRecordContext(
                    provenance_pointers=provenance_pointers,
                    storage_notes=(
                        "first executable protein-variant slice from IntAct mutation "
                        "export",
                    ),
                ),
                notes=notes,
            )
            records_by_key[key] = record
    return tuple(record for _, record in sorted(records_by_key.items()))


def build_protein_variant_summary_library(
    protein_library: SummaryLibrarySchema | Iterable[ProteinSummaryRecord],
    *,
    supported_accessions: Iterable[str],
    uniprot_root: Path = DEFAULT_UNIPROT_ROOT,
    intact_mutation_path: Path = DEFAULT_INTACT_MUTATION_PATH,
    library_id: str = DEFAULT_LIBRARY_ID,
    schema_version: int = 2,
    source_manifest_id: str | None = None,
) -> SummaryLibrarySchema:
    records = materialize_protein_variant_records(
        protein_library,
        uniprot_root=uniprot_root,
        intact_mutation_path=intact_mutation_path,
        supported_accessions=supported_accessions,
    )
    manifest_id = (
        source_manifest_id
        or (
            protein_library.source_manifest_id
            if isinstance(protein_library, SummaryLibrarySchema)
            else None
        )
    )
    if manifest_id:
        manifest_id = (
            f"{manifest_id}|IntActMutation:{INTACT_RELEASE_VERSION}|VariantSupport:p54"
        )
    return SummaryLibrarySchema(
        library_id=library_id,
        records=records,
        schema_version=schema_version,
        source_manifest_id=manifest_id,
        index_guidance=(
            "route protein variants by protein_ref and variant_signature",
            "preserve merged mutation signatures for leakage-aware family grouping",
        ),
        storage_guidance=(
            "treat protein variants as a compact feature-cache layer",
            "keep construct lineage deferred until explicit construct evidence exists",
        ),
        lazy_loading_guidance=(
            "merge corroborating UniProt and IntAct mutation evidence on the same signature",
            "defer full variant annotations and construct-heavy payloads until selection",
        ),
    )


def build_protein_variant_summary_library_from_paths(
    *,
    protein_summary_library_path: Path = DEFAULT_PROTEIN_SUMMARY_LIBRARY_PATH,
    variant_evidence_paths: Iterable[Path] = DEFAULT_VARIANT_EVIDENCE_PATHS,
    uniprot_root: Path = DEFAULT_UNIPROT_ROOT,
    intact_mutation_path: Path = DEFAULT_INTACT_MUTATION_PATH,
    library_id: str = DEFAULT_LIBRARY_ID,
) -> SummaryLibrarySchema:
    protein_library = _load_protein_library(protein_summary_library_path)
    supported = _supported_accessions(variant_evidence_paths)
    return build_protein_variant_summary_library(
        protein_library,
        supported_accessions=supported,
        uniprot_root=uniprot_root,
        intact_mutation_path=intact_mutation_path,
        library_id=library_id,
    )


__all__ = [
    "DEFAULT_INTACT_MUTATION_PATH",
    "DEFAULT_OUTPUT_PATH",
    "DEFAULT_PROTEIN_SUMMARY_LIBRARY_PATH",
    "DEFAULT_UNIPROT_ROOT",
    "DEFAULT_VARIANT_EVIDENCE_PATHS",
    "DEFAULT_LIBRARY_ID",
    "build_protein_variant_summary_library",
    "build_protein_variant_summary_library_from_paths",
    "materialize_protein_variant_records",
]
