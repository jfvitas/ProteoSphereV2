from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from connectors.bindingdb.parsers import parse_bindingdb_assays
from core.canonical.ligand import CanonicalLigand
from core.canonical.registry import CanonicalEntityRegistry
from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)
from core.storage.canonical_store import (
    CanonicalStore,
    CanonicalStoreArtifactPointer,
    CanonicalStoreRecord,
    CanonicalStoreSourceRef,
)
from execution.acquire.alphafold_snapshot import (
    AlphaFoldConfidenceSummary,
    AlphaFoldProvenance,
    AlphaFoldSnapshotRecord,
)
from execution.ingest.assays import AssayIngestResult, ingest_bindingdb_assays
from execution.ingest.sequences import (
    DEFAULT_PARSER_VERSION,
    SequenceIngestResult,
    ingest_sequence_records,
)
from execution.ingest.structures import StructureIngestResult, ingest_structure_records

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOOTSTRAP_SUMMARY = ROOT / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
DEFAULT_LOCAL_REGISTRY_SUMMARY = ROOT / "data" / "raw" / "local_registry_runs" / "LATEST.json"
DEFAULT_BINDINGDB_LOCAL_SUMMARY = ROOT / "data" / "raw" / "bindingdb_dump_local" / "LATEST.json"
DEFAULT_CANONICAL_ROOT = ROOT / "data" / "canonical"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _repo_relative(path: Path, *, repo_root: Path = ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _normalize_strings(values: Any, *, upper: bool = False) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if not text:
            continue
        normalized = text.upper() if upper else text
        ordered.setdefault(normalized.casefold(), normalized)
    return tuple(ordered.values())


def _normalize_ints(values: Any) -> tuple[int, ...]:
    normalized: list[int] = []
    seen: set[int] = set()
    for value in _iter_values(values):
        if value in (None, ""):
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed in seen:
            continue
        seen.add(parsed)
        normalized.append(parsed)
    return tuple(normalized)


def _normalize_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _timestamp_slug() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _source_result(summary: Mapping[str, Any], source_name: str) -> Mapping[str, Any] | None:
    for item in summary.get("results") or ():
        if isinstance(item, Mapping) and _clean_text(item.get("source")) == source_name:
            return item
    return None


def _source_manifest(summary: Mapping[str, Any], source_name: str) -> SourceReleaseManifest | None:
    result = _source_result(summary, source_name)
    if result is None:
        return None
    manifest_payload = result.get("manifest")
    if not isinstance(manifest_payload, Mapping):
        return None
    return validate_source_release_manifest_payload(dict(manifest_payload))


def _downloaded_paths(
    summary: Mapping[str, Any],
    source_name: str,
    *,
    repo_root: Path = ROOT,
) -> tuple[Path, ...]:
    result = _source_result(summary, source_name)
    if result is None:
        return ()
    resolved: list[Path] = []
    for item in result.get("downloaded_files") or ():
        path = repo_root / str(item)
        if path.exists():
            resolved.append(path)
    return tuple(resolved)


def _first_present_json(paths: Sequence[Path]) -> tuple[Path, ...]:
    return tuple(path for path in paths if path.suffix.casefold() == ".json")


def _alphafold_confidence(payload: Mapping[str, Any]) -> AlphaFoldConfidenceSummary:
    fractions: dict[str, float] = {}
    for key in (
        "fractionPlddtVeryLow",
        "fractionPlddtLow",
        "fractionPlddtConfident",
        "fractionPlddtVeryHigh",
        "fractionVeryLow",
        "fractionLow",
        "fractionConfident",
        "fractionVeryHigh",
    ):
        value = _normalize_float(payload.get(key))
        if value is not None:
            fractions[key] = value
    return AlphaFoldConfidenceSummary(
        global_metric_value=_normalize_float(payload.get("globalMetricValue")),
        confidence_fractions=fractions,
    )


def _alphafold_asset_map(
    summary: Mapping[str, Any],
    *,
    repo_root: Path = ROOT,
) -> dict[str, tuple[CanonicalStoreArtifactPointer, ...]]:
    pointers_by_accession: dict[str, list[CanonicalStoreArtifactPointer]] = {}
    for path in _downloaded_paths(summary, "alphafold", repo_root=repo_root):
        if path.suffix.casefold() not in {".pdb", ".cif", ".bcif"}:
            continue
        accession = path.parent.name
        pointer = CanonicalStoreArtifactPointer(
            artifact_kind="structure",
            pointer=_repo_relative(path, repo_root=repo_root),
            source_name="AlphaFold DB",
            source_record_id=accession,
        )
        pointers_by_accession.setdefault(accession.upper(), []).append(pointer)
    return {
        accession: tuple(pointers)
        for accession, pointers in sorted(pointers_by_accession.items())
    }


def load_uniprot_entries(
    summary: Mapping[str, Any],
    *,
    repo_root: Path = ROOT,
) -> tuple[dict[str, Any], ...]:
    entries: list[dict[str, Any]] = []
    for path in _first_present_json(_downloaded_paths(summary, "uniprot", repo_root=repo_root)):
        payload = _read_json(path)
        if isinstance(payload, Mapping):
            entries.append(dict(payload))
    return tuple(entries)


def load_bindingdb_payloads(
    summary: Mapping[str, Any],
    *,
    repo_root: Path = ROOT,
) -> tuple[dict[str, Any], ...]:
    payloads: list[dict[str, Any]] = []
    for path in _first_present_json(
        _downloaded_paths(summary, "bindingdb", repo_root=repo_root)
    ):
        payload = _read_json(path)
        if isinstance(payload, Mapping):
            payloads.append(dict(payload))
    return tuple(payloads)


def load_bindingdb_local_assay_rows(
    summary_path: Path | None,
    *,
    accessions: Sequence[str] | None = None,
) -> tuple[dict[str, Any], ...]:
    if summary_path is None or not summary_path.exists():
        return ()
    payload = _read_json(summary_path)
    if not isinstance(payload, Mapping):
        return ()
    selected = {
        accession.casefold(): accession for accession in _normalize_strings(accessions, upper=True)
    }
    rows: list[dict[str, Any]] = []
    for slice_payload in payload.get("slices") or ():
        if not isinstance(slice_payload, Mapping):
            continue
        accession = _clean_text(slice_payload.get("accession")).upper()
        if selected and accession.casefold() not in selected:
            continue
        for row in slice_payload.get("assay_rows") or ():
            if isinstance(row, Mapping):
                rows.append(dict(row))
    return tuple(rows)


def _bindingdb_local_summary_stats(
    summary_path: Path | None,
    *,
    accessions: Sequence[str] | None = None,
) -> dict[str, Any]:
    if summary_path is None or not summary_path.exists():
        return {
            "summary_path": None,
            "matched_accession_count": 0,
            "total_accession_count": 0,
            "assay_row_count": 0,
            "measurement_result_count": 0,
        }
    payload = _read_json(summary_path)
    if not isinstance(payload, Mapping):
        return {
            "summary_path": str(summary_path),
            "matched_accession_count": 0,
            "total_accession_count": 0,
            "assay_row_count": 0,
            "measurement_result_count": 0,
        }
    selected = {
        accession.casefold(): accession for accession in _normalize_strings(accessions, upper=True)
    }
    matched_accession_count = 0
    assay_row_count = 0
    measurement_result_count = 0
    total_accession_count = 0
    for slice_payload in payload.get("slices") or ():
        if not isinstance(slice_payload, Mapping):
            continue
        total_accession_count += 1
        accession = _clean_text(slice_payload.get("accession")).upper()
        if selected and accession.casefold() not in selected:
            continue
        matched_accession_count += 1
        assay_row_count += int(slice_payload.get("assay_row_count") or 0)
        measurement_result_count += int(slice_payload.get("measurement_result_count") or 0)
    return {
        "summary_path": str(summary_path),
        "matched_accession_count": matched_accession_count,
        "total_accession_count": total_accession_count,
        "assay_row_count": assay_row_count,
        "measurement_result_count": measurement_result_count,
    }


def resolve_bindingdb_local_summary_path(
    summary_path: Path | None,
    *,
    accessions: Sequence[str] | None = None,
) -> Path | None:
    if summary_path is None:
        return None
    if summary_path.exists():
        primary_stats = _bindingdb_local_summary_stats(
            summary_path,
            accessions=accessions,
        )
        if primary_stats["assay_row_count"] > 0:
            return summary_path
    search_root = summary_path.parent
    if not search_root.exists():
        return summary_path if summary_path.exists() else None
    candidates: list[tuple[int, int, float, Path]] = []
    for candidate in search_root.rglob("summary.json"):
        stats = _bindingdb_local_summary_stats(candidate, accessions=accessions)
        if stats["assay_row_count"] <= 0:
            continue
        candidates.append(
            (
                int(stats["matched_accession_count"]),
                int(stats["assay_row_count"]),
                candidate.stat().st_mtime,
                candidate,
            )
        )
    if not candidates:
        return summary_path if summary_path.exists() else None
    candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return candidates[0][3]


def _bindingdb_ligands(payloads: Sequence[Mapping[str, Any]]) -> tuple[CanonicalLigand, ...]:
    by_ligand_id: dict[str, CanonicalLigand] = {}
    for payload in payloads:
        for record in parse_bindingdb_assays(payload, source="BindingDB"):
            monomer_id = _clean_text(record.monomer_id)
            if not monomer_id:
                continue
            ligand_id = f"bindingdb:{monomer_id}"
            existing = by_ligand_id.get(ligand_id)
            candidate = CanonicalLigand(
                ligand_id=ligand_id,
                name=_clean_text(record.ligand_inchi_key)
                or _clean_text(record.ligand_smiles)
                or f"BindingDB ligand {monomer_id}",
                source="BindingDB",
                source_id=monomer_id,
                smiles=_optional_text(record.ligand_smiles),
                inchikey=_optional_text(record.ligand_inchi_key),
                provenance=("materialized_from_bindingdb_payload",),
            )
            if existing is None:
                by_ligand_id[ligand_id] = candidate
                continue
            by_ligand_id[ligand_id] = CanonicalLigand(
                ligand_id=existing.ligand_id,
                name=existing.name
                if existing.name != f"BindingDB ligand {monomer_id}"
                else candidate.name,
                source=existing.source,
                source_id=existing.source_id,
                smiles=existing.smiles or candidate.smiles,
                inchi=existing.inchi or candidate.inchi,
                inchikey=existing.inchikey or candidate.inchikey,
                formula=existing.formula or candidate.formula,
                charge=existing.charge if existing.charge is not None else candidate.charge,
                synonyms=tuple(dict.fromkeys((*existing.synonyms, *candidate.synonyms))),
                provenance=tuple(dict.fromkeys((*existing.provenance, *candidate.provenance))),
            )
    return tuple(by_ligand_id.values())


def load_alphafold_records(
    summary: Mapping[str, Any],
    *,
    first_record_only: bool = True,
    repo_root: Path = ROOT,
) -> tuple[AlphaFoldSnapshotRecord, ...]:
    manifest = _source_manifest(summary, "alphafold")
    if manifest is None:
        return ()
    fetched_at = _clean_text(summary.get("generated_at")) or _utc_now().isoformat()
    records: list[AlphaFoldSnapshotRecord] = []
    for path in _first_present_json(
        _downloaded_paths(summary, "alphafold", repo_root=repo_root)
    ):
        if not path.name.endswith(".prediction.json"):
            continue
        payload = _read_json(path)
        if not isinstance(payload, list):
            continue
        items = payload[:1] if first_record_only else payload
        for item in items:
            if not isinstance(item, Mapping):
                continue
            qualifier = _clean_text(item.get("uniprotAccession") or path.parent.name).upper()
            model_entity_id = (
                _clean_text(item.get("modelEntityId") or item.get("entryId") or qualifier)
                or qualifier
            )
            records.append(
                AlphaFoldSnapshotRecord(
                    structure_kind="prediction",
                    qualifier=qualifier,
                    model_entity_id=model_entity_id,
                    provenance=AlphaFoldProvenance(
                        source_release=manifest,
                        manifest_id=manifest.manifest_id,
                        qualifier=qualifier,
                        endpoint=_repo_relative(path, repo_root=repo_root),
                        fetched_at=fetched_at,
                        source_locator=manifest.source_locator,
                        retrieval_mode=manifest.retrieval_mode,
                        provider_id=_optional_text(item.get("providerId")),
                        tool_used=_optional_text(item.get("toolUsed")),
                        include_complexes=False,
                        include_annotations=False,
                        annotation_type=None,
                    ),
                    confidence=_alphafold_confidence(item),
                    raw_summary=dict(item),
                    entry_id=_optional_text(item.get("entryId")),
                    sequence_checksum=_optional_text(item.get("sequenceChecksum")),
                    latest_version=(
                        int(item["latestVersion"])
                        if item.get("latestVersion") not in (None, "")
                        else None
                    ),
                    all_versions=_normalize_ints(item.get("allVersions")),
                    uniprot_accessions=_normalize_strings(item.get("uniprotAccession"), upper=True),
                    uniprot_ids=_normalize_strings(item.get("uniprotId"), upper=True),
                    entity_type=_optional_text(item.get("entityType")),
                    provider_id=_optional_text(item.get("providerId")),
                    tool_used=_optional_text(item.get("toolUsed")),
                    is_uniprot=(
                        bool(item.get("isUniProt"))
                        if item.get("isUniProt") is not None
                        else None
                    ),
                    is_uniprot_reviewed=(
                        bool(item.get("isUniProtReviewed"))
                        if item.get("isUniProtReviewed") is not None
                        else None
                    ),
                    is_uniprot_reference_proteome=(
                        bool(item.get("isUniProtReferenceProteome"))
                        if item.get("isUniProtReferenceProteome") is not None
                        else None
                    ),
                    is_isoform=(
                        bool(item.get("isIsoform"))
                        if item.get("isIsoform") is not None
                        else None
                    ),
                    is_amdata=(
                        bool(item.get("isAMdata"))
                        if item.get("isAMdata") is not None
                        else None
                    ),
                    gene=_normalize_strings(item.get("gene")),
                    tax_id=_normalize_ints(item.get("taxId")),
                    organism_scientific_name=_normalize_strings(
                        item.get("organismScientificName")
                    ),
                    sequence_start=(
                        int(item["sequenceStart"])
                        if item.get("sequenceStart") not in (None, "")
                        else None
                    ),
                    sequence_end=(
                        int(item["sequenceEnd"])
                        if item.get("sequenceEnd") not in (None, "")
                        else None
                    ),
                    sequence=_optional_text(item.get("sequence")),
                    uniprot_start=(
                        int(item["uniprotStart"])
                        if item.get("uniprotStart") not in (None, "")
                        else None
                    ),
                    uniprot_end=(
                        int(item["uniprotEnd"])
                        if item.get("uniprotEnd") not in (None, "")
                        else None
                    ),
                    uniprot_sequence=_optional_text(item.get("uniprotSequence")),
                    asset_urls={
                        key: value
                        for key, value in {
                            "bcif": _optional_text(item.get("bcifUrl")),
                            "cif": _optional_text(item.get("cifUrl")),
                            "pdb": _optional_text(item.get("pdbUrl")),
                            "msa": _optional_text(item.get("msaUrl")),
                            "plddt_doc": _optional_text(item.get("plddtDocUrl")),
                            "pae_doc": _optional_text(item.get("paeDocUrl")),
                            "pae_image": _optional_text(item.get("paeImageUrl")),
                        }.items()
                        if value is not None
                    },
                )
            )
    return tuple(records)


def _record_statuses(
    sequence_result: SequenceIngestResult,
    structure_result: StructureIngestResult,
    assay_result: AssayIngestResult,
) -> tuple[str, str]:
    statuses = (sequence_result.status, structure_result.status, assay_result.status)
    if "conflict" in statuses:
        return "conflict", "one_or_more_lanes_reported_conflicts"
    if any(status in {"partial", "unresolved", "ambiguous"} for status in statuses):
        if any(status in {"ready", "resolved"} for status in statuses):
            return "partial", "one_or_more_lanes_preserved_unresolved_cases"
        return "unresolved", "no_lane_fully_resolved"
    return "ready", "all_manifest_driven_lanes_resolved"


def _protein_store_records(
    sequence_result: SequenceIngestResult,
    *,
    source_manifest: SourceReleaseManifest | None,
) -> tuple[CanonicalStoreRecord, ...]:
    records: list[CanonicalStoreRecord] = []
    provenance_by_canonical_id = {
        outcome.canonical_protein.canonical_id: outcome.provenance_record.provenance_id
        for outcome in sequence_result.outcomes
        if outcome.canonical_protein is not None and outcome.provenance_record is not None
    }
    for protein in sequence_result.canonical_proteins:
        source_ref = CanonicalStoreSourceRef(
            source_name="UniProt",
            source_record_id=protein.accession,
            source_manifest_id=source_manifest.manifest_id if source_manifest else None,
            source_locator=source_manifest.source_locator if source_manifest else None,
            source_keys={"accession": protein.accession},
        )
        provenance_refs = (
            (provenance_by_canonical_id[protein.canonical_id],)
            if protein.canonical_id in provenance_by_canonical_id
            else ()
        )
        records.append(
            CanonicalStoreRecord(
                canonical_id=protein.canonical_id,
                entity_kind="protein",
                canonical_payload=protein.to_dict(),
                source_refs=(source_ref,),
                aliases=(protein.accession, *protein.gene_names),
                provenance_refs=provenance_refs,
                notes=("materialized_from_raw_bootstrap",),
            )
        )
    return tuple(records)


def _assay_store_records(
    assay_result: AssayIngestResult,
    *,
    source_manifest: SourceReleaseManifest | None,
) -> tuple[CanonicalStoreRecord, ...]:
    records: list[CanonicalStoreRecord] = []
    for assay in assay_result.canonical_assays:
        source_ref = CanonicalStoreSourceRef(
            source_name=assay.source,
            source_record_id=assay.source_id,
            source_manifest_id=source_manifest.manifest_id if source_manifest else None,
            source_locator=source_manifest.source_locator if source_manifest else None,
            source_keys={"target_id": assay.target_id, "ligand_id": assay.ligand_id},
        )
        records.append(
            CanonicalStoreRecord(
                canonical_id=assay.assay_id,
                entity_kind="assay",
                canonical_payload=assay.to_dict(),
                source_refs=(source_ref,),
                aliases=(assay.source_id,),
                provenance_refs=assay.provenance,
                notes=("materialized_from_raw_bootstrap",),
            )
        )
    return tuple(records)


def _ligand_store_records(
    ligands: Sequence[CanonicalLigand],
    *,
    source_manifest: SourceReleaseManifest | None,
) -> tuple[CanonicalStoreRecord, ...]:
    records: list[CanonicalStoreRecord] = []
    for ligand in ligands:
        source_ref = CanonicalStoreSourceRef(
            source_name=ligand.source,
            source_record_id=ligand.source_id,
            source_manifest_id=source_manifest.manifest_id if source_manifest else None,
            source_locator=source_manifest.source_locator if source_manifest else None,
            source_keys={"ligand_id": ligand.ligand_id},
        )
        records.append(
            CanonicalStoreRecord(
                canonical_id=f"ligand:{ligand.ligand_id}",
                entity_kind="ligand",
                canonical_payload=ligand.to_dict(),
                source_refs=(source_ref,),
                aliases=tuple(
                    alias
                    for alias in (
                        ligand.ligand_id,
                        ligand.source_id,
                        ligand.inchikey,
                        ligand.smiles,
                    )
                    if alias
                ),
                provenance_refs=ligand.provenance,
                notes=("materialized_from_raw_bootstrap", "ligand_lane_record"),
            )
        )
    return tuple(records)


def _structure_store_records(
    structure_result: StructureIngestResult,
    *,
    asset_map: Mapping[str, tuple[CanonicalStoreArtifactPointer, ...]],
) -> tuple[CanonicalStoreRecord, ...]:
    records: list[CanonicalStoreRecord] = []
    for protein in structure_result.proteins:
        accession = (
            protein.primary_external_id
            if protein.primary_external_id_type.casefold() == "uniprot accession".casefold()
            else None
        )
        artifact_pointers = asset_map.get(_clean_text(accession).upper(), ())
        records.append(
            CanonicalStoreRecord(
                canonical_id=protein.protein_id_internal,
                entity_kind="structure",
                canonical_payload=protein.to_dict(),
                source_refs=(
                    CanonicalStoreSourceRef(
                        source_name="AlphaFold DB",
                        source_record_id=protein.primary_external_id,
                        source_keys={"external_id_type": protein.primary_external_id_type},
                    ),
                ),
                artifact_pointers=artifact_pointers,
                aliases=(protein.primary_external_id,),
                provenance_refs=protein.provenance_refs,
                notes=("structure_lane_record",),
            )
        )
    for chain in structure_result.chains:
        records.append(
            CanonicalStoreRecord(
                canonical_id=chain.chain_id_internal,
                entity_kind="structure",
                canonical_payload=chain.to_dict(),
                source_refs=(
                    CanonicalStoreSourceRef(
                        source_name=chain.structure_source,
                        source_record_id=chain.structure_id,
                        source_keys={"chain_label": chain.chain_label},
                    ),
                ),
                provenance_refs=chain.provenance_refs,
                notes=("structure_lane_record", "chain"),
            )
        )
    for complex_record in structure_result.complexes:
        records.append(
            CanonicalStoreRecord(
                canonical_id=complex_record.complex_id_internal,
                entity_kind="structure",
                canonical_payload=complex_record.to_dict(),
                source_refs=(
                    CanonicalStoreSourceRef(
                        source_name=complex_record.structure_source,
                        source_record_id=complex_record.structure_id,
                        source_keys={"assembly_id": complex_record.assembly_id or ""},
                    ),
                ),
                provenance_refs=complex_record.provenance_refs,
                notes=("structure_lane_record", "complex"),
            )
        )
    return tuple(records)


def _latest_local_registry_info(summary_path: Path | None) -> dict[str, Any]:
    if summary_path is None or not summary_path.exists():
        return {}
    payload = _read_json(summary_path)
    if not isinstance(payload, Mapping):
        return {}
    return {
        "summary_path": _repo_relative(summary_path, repo_root=summary_path.resolve().parents[3]),
        "stamp": payload.get("stamp"),
        "imported_source_count": payload.get("imported_source_count"),
        "selected_source_count": payload.get("selected_source_count"),
    }


def _record_counts(
    sequence_result: SequenceIngestResult,
    structure_result: StructureIngestResult,
    assay_result: AssayIngestResult,
    canonical_store: CanonicalStore,
) -> dict[str, int]:
    store_counts: dict[str, int] = {}
    for record in canonical_store.records:
        store_counts[record.entity_kind] = store_counts.get(record.entity_kind, 0) + 1
    return {
        "protein": len(sequence_result.canonical_proteins),
        "ligand": store_counts.get("ligand", 0),
        "assay": len(assay_result.canonical_assays),
        "structure": store_counts.get("structure", 0),
        "store_total": len(canonical_store.records),
    }


def _unresolved_counts(
    sequence_result: SequenceIngestResult,
    structure_result: StructureIngestResult,
    assay_result: AssayIngestResult,
) -> dict[str, int]:
    return {
        "sequence_conflicts": len(sequence_result.conflicts),
        "sequence_unresolved_references": len(sequence_result.unresolved_references),
        "structure_conflicts": len(structure_result.conflicts),
        "structure_unresolved_references": len(structure_result.unresolved_references),
        "assay_conflicts": len(assay_result.conflicts),
        "assay_unresolved_cases": len(assay_result.unresolved_cases),
    }


@dataclass(frozen=True, slots=True)
class RawCanonicalMaterializationResult:
    created_at: str
    status: str
    reason: str
    run_id: str
    bootstrap_summary_path: str
    canonical_root: str
    sequence_result: SequenceIngestResult
    structure_result: StructureIngestResult
    assay_result: AssayIngestResult
    canonical_store: CanonicalStore
    skipped_sources: tuple[dict[str, Any], ...] = ()
    local_registry: Mapping[str, Any] = field(default_factory=dict)
    bindingdb_selection: Mapping[str, Any] = field(default_factory=dict)
    record_counts: Mapping[str, int] = field(default_factory=dict)
    unresolved_counts: Mapping[str, int] = field(default_factory=dict)
    output_paths: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "status": self.status,
            "reason": self.reason,
            "run_id": self.run_id,
            "bootstrap_summary_path": self.bootstrap_summary_path,
            "canonical_root": self.canonical_root,
            "sequence_result": self.sequence_result.to_dict(),
            "structure_result": self.structure_result.to_dict(),
            "assay_result": self.assay_result.to_dict(),
            "canonical_store": self.canonical_store.to_dict(),
            "skipped_sources": [dict(item) for item in self.skipped_sources],
            "local_registry": dict(self.local_registry),
            "bindingdb_selection": dict(self.bindingdb_selection),
            "record_counts": dict(self.record_counts),
            "unresolved_counts": dict(self.unresolved_counts),
            "output_paths": dict(self.output_paths),
        }


def _bindingdb_selection_info(
    *,
    selected_summary_path: Path | None,
    accessions: Sequence[str],
    local_rows: Sequence[Mapping[str, Any]],
    rest_payloads: Sequence[Mapping[str, Any]],
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    summary_stats = _bindingdb_local_summary_stats(
        selected_summary_path,
        accessions=accessions,
    )
    local_row_count = len(local_rows)
    rest_payload_count = len(rest_payloads)
    if local_row_count > 0:
        selection_mode = "local_summary"
    elif rest_payload_count > 0:
        selection_mode = "rest_fallback"
    else:
        selection_mode = "no_bindingdb_records"
    return {
        "selected_summary_path": (
            _repo_relative(selected_summary_path, repo_root=repo_root)
            if selected_summary_path is not None and selected_summary_path.exists()
            else None
        ),
        "selection_mode": selection_mode,
        "local_row_count": local_row_count,
        "rest_payload_count": rest_payload_count,
        "matched_accession_count": int(summary_stats["matched_accession_count"]),
        "summary_assay_row_count": int(summary_stats["assay_row_count"]),
        "summary_measurement_result_count": int(summary_stats["measurement_result_count"]),
    }


def materialize_raw_bootstrap_to_canonical(
    *,
    bootstrap_summary_path: Path = DEFAULT_BOOTSTRAP_SUMMARY,
    canonical_root: Path = DEFAULT_CANONICAL_ROOT,
    local_registry_summary_path: Path | None = DEFAULT_LOCAL_REGISTRY_SUMMARY,
    bindingdb_local_summary_path: Path | None = DEFAULT_BINDINGDB_LOCAL_SUMMARY,
    first_alphafold_record_only: bool = True,
    run_id: str | None = None,
) -> RawCanonicalMaterializationResult:
    summary_payload = _read_json(bootstrap_summary_path)
    if not isinstance(summary_payload, Mapping):
        raise TypeError("bootstrap summary must be a mapping")
    repo_root = bootstrap_summary_path.resolve().parents[3]

    resolved_run_id = _clean_text(run_id) or f"raw-canonical-{_timestamp_slug()}"
    registry = CanonicalEntityRegistry()

    uniprot_manifest = _source_manifest(summary_payload, "uniprot")
    bindingdb_manifest = _source_manifest(summary_payload, "bindingdb")
    bindingdb_payloads = load_bindingdb_payloads(summary_payload, repo_root=repo_root)
    sequence_result = ingest_sequence_records(
        load_uniprot_entries(summary_payload, repo_root=repo_root),
        registry=registry,
        source_release=uniprot_manifest.to_dict() if uniprot_manifest is not None else None,
        parser_version=DEFAULT_PARSER_VERSION,
    )
    selected_bindingdb_local_summary = resolve_bindingdb_local_summary_path(
        bindingdb_local_summary_path,
        accessions=tuple(protein.accession for protein in sequence_result.canonical_proteins),
    )
    bindingdb_local_rows = load_bindingdb_local_assay_rows(
        selected_bindingdb_local_summary,
        accessions=tuple(protein.accession for protein in sequence_result.canonical_proteins),
    )
    bindingdb_records: tuple[dict[str, Any], ...] = (
        bindingdb_local_rows if bindingdb_local_rows else bindingdb_payloads
    )
    ligands = _bindingdb_ligands(bindingdb_records)
    registry.register_many(ligands)
    structure_result = ingest_structure_records(
        load_alphafold_records(
            summary_payload,
            first_record_only=first_alphafold_record_only,
            repo_root=repo_root,
        ),
        provenance=sequence_result.provenance_records,
        registry=registry,
    )
    assay_result = ingest_bindingdb_assays(
        bindingdb_records,
        registry=registry,
        source_name="BindingDB",
        acquired_at=_clean_text(summary_payload.get("generated_at")) or _utc_now().isoformat(),
        parser_version=DEFAULT_PARSER_VERSION,
        release_version=bindingdb_manifest.release_version if bindingdb_manifest else None,
        run_id=resolved_run_id,
    )

    store_records = (
        *_protein_store_records(sequence_result, source_manifest=uniprot_manifest),
        *_ligand_store_records(ligands, source_manifest=bindingdb_manifest),
        *_assay_store_records(assay_result, source_manifest=bindingdb_manifest),
        *_structure_store_records(
            structure_result,
            asset_map=_alphafold_asset_map(summary_payload, repo_root=repo_root),
        ),
    )
    canonical_store = CanonicalStore(records=tuple(store_records))
    status, reason = _record_statuses(sequence_result, structure_result, assay_result)

    skipped_sources: list[dict[str, Any]] = []
    if _source_result(summary_payload, "rcsb_pdbe") is not None:
        skipped_sources.append(
            {
                "source": "rcsb_pdbe",
                "reason": (
                    "entry_json_and_mmcif_present_but_polymer_entity_and_assembly_payloads_missing"
                ),
                "status": "skipped_for_local_canonical_materialization",
            }
        )
    if _source_result(summary_payload, "pdbbind") is not None:
        skipped_sources.append(
            {
                "source": "pdbbind",
                "reason": "manual_acquisition_gate_not_yet_materialized",
                "status": "skipped_for_local_canonical_materialization",
            }
        )

    run_root = canonical_root / "runs" / resolved_run_id
    output_paths = {
        "sequence_result": _repo_relative(run_root / "sequence_result.json", repo_root=repo_root),
        "structure_result": _repo_relative(
            run_root / "structure_result.json",
            repo_root=repo_root,
        ),
        "assay_result": _repo_relative(run_root / "assay_result.json", repo_root=repo_root),
        "canonical_store": _repo_relative(run_root / "canonical_store.json", repo_root=repo_root),
        "materialization_report": _repo_relative(
            run_root / "materialization_report.json",
            repo_root=repo_root,
        ),
        "latest": _repo_relative(canonical_root / "LATEST.json", repo_root=repo_root),
    }
    created_at = _utc_now().isoformat()

    result = RawCanonicalMaterializationResult(
        created_at=created_at,
        status=status,
        reason=reason,
        run_id=resolved_run_id,
        bootstrap_summary_path=_repo_relative(bootstrap_summary_path, repo_root=repo_root),
        canonical_root=_repo_relative(canonical_root, repo_root=repo_root),
        sequence_result=sequence_result,
        structure_result=structure_result,
        assay_result=assay_result,
        canonical_store=canonical_store,
        skipped_sources=tuple(skipped_sources),
        local_registry=_latest_local_registry_info(local_registry_summary_path),
        bindingdb_selection=_bindingdb_selection_info(
            selected_summary_path=selected_bindingdb_local_summary,
            accessions=tuple(protein.accession for protein in sequence_result.canonical_proteins),
            local_rows=bindingdb_local_rows,
            rest_payloads=bindingdb_payloads,
            repo_root=repo_root,
        ),
        record_counts=_record_counts(
            sequence_result,
            structure_result,
            assay_result,
            canonical_store,
        ),
        unresolved_counts=_unresolved_counts(sequence_result, structure_result, assay_result),
        output_paths=output_paths,
    )

    _write_json(run_root / "sequence_result.json", sequence_result.to_dict())
    _write_json(run_root / "structure_result.json", structure_result.to_dict())
    _write_json(run_root / "assay_result.json", assay_result.to_dict())
    _write_json(run_root / "canonical_store.json", canonical_store.to_dict())
    _write_json(run_root / "materialization_report.json", result.to_dict())
    _write_json(canonical_root / "LATEST.json", result.to_dict())
    return result


__all__ = [
    "DEFAULT_BINDINGDB_LOCAL_SUMMARY",
    "DEFAULT_BOOTSTRAP_SUMMARY",
    "DEFAULT_CANONICAL_ROOT",
    "DEFAULT_LOCAL_REGISTRY_SUMMARY",
    "RawCanonicalMaterializationResult",
    "load_alphafold_records",
    "load_bindingdb_local_assay_rows",
    "load_bindingdb_payloads",
    "load_uniprot_entries",
    "materialize_raw_bootstrap_to_canonical",
]
