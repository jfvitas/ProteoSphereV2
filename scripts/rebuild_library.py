from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.storage.reference_warehouse import (
    ReferenceWarehouseEntityFamily,
    ReferenceWarehouseValidation,
)
from scripts.reference_warehouse_common import (
    DEFAULT_WAREHOUSE_CATALOG,
    DEFAULT_WAREHOUSE_MANIFEST,
    DEFAULT_WAREHOUSE_ROOT,
    REPO_ROOT,
    build_catalog,
    build_manifest,
    build_source_descriptors_from_coverage,
    load_summary_library,
    read_json,
    sync_catalog_metadata,
    write_json,
    write_partition_rows,
)

DEFAULT_PROTEIN_LIBRARY = REPO_ROOT / "artifacts" / "status" / "protein_summary_library.json"
DEFAULT_VARIANT_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "protein_variant_summary_library.json"
)
DEFAULT_STRUCTURE_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
)
DEFAULT_INTACT_LIBRARY = REPO_ROOT / "artifacts" / "status" / "intact_local_summary_library.json"
DEFAULT_REACTOME_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "reactome_local_summary_library.json"
)
DEFAULT_LIGAND_ROWS = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_PROTEIN_SIMILARITY = (
    REPO_ROOT / "artifacts" / "status" / "protein_similarity_signature_preview.json"
)
DEFAULT_STRUCTURE_SIMILARITY = (
    REPO_ROOT / "artifacts" / "status" / "structure_similarity_signature_preview.json"
)
DEFAULT_LIGAND_SIMILARITY = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_preview.json"
)
DEFAULT_INTERACTION_SIMILARITY = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
)
DEFAULT_LEAKAGE_GROUPS = REPO_ROOT / "artifacts" / "status" / "leakage_group_preview.json"
DEFAULT_SOURCE_COVERAGE = REPO_ROOT / "artifacts" / "status" / "source_coverage_matrix.json"
DEFAULT_CANONICAL_LATEST = REPO_ROOT / "data" / "canonical" / "LATEST.json"
DEFAULT_WAREHOUSE_SUMMARY = DEFAULT_WAREHOUSE_ROOT / "warehouse_summary.json"


SOURCE_OVERRIDES: dict[str, dict[str, Any]] = {
    "bindingdb": {
        "license_scope": "internal_only",
        "redistributable": False,
        "public_export_allowed": False,
        "refresh_cadence": "monthly",
        "partition_strategy": "source/snapshot/accession",
    },
    "uniprot": {
        "license_scope": "public_metadata",
        "redistributable": True,
        "public_export_allowed": True,
        "refresh_cadence": "monthly",
        "partition_strategy": "source/snapshot/accession",
    },
    "alphafold": {
        "license_scope": "public_metadata",
        "redistributable": True,
        "public_export_allowed": True,
        "refresh_cadence": "monthly",
        "partition_strategy": "source/snapshot/accession",
    },
    "rcsb_pdbe": {
        "license_scope": "public_metadata",
        "redistributable": True,
        "public_export_allowed": True,
        "refresh_cadence": "weekly",
        "partition_strategy": "source/snapshot/pdb_id",
    },
    "intact": {
        "license_scope": "public_metadata",
        "redistributable": True,
        "public_export_allowed": True,
        "refresh_cadence": "monthly",
        "partition_strategy": "source/snapshot/accession",
    },
    "biogrid": {
        "license_scope": "internal_only",
        "redistributable": False,
        "public_export_allowed": False,
        "refresh_cadence": "monthly",
        "partition_strategy": "source/snapshot/accession",
    },
    "elm": {
        "license_scope": "public_metadata",
        "redistributable": True,
        "public_export_allowed": True,
        "refresh_cadence": "manual",
        "partition_strategy": "source/snapshot/accession",
    },
    "sabio_rk": {
        "license_scope": "restricted",
        "redistributable": False,
        "public_export_allowed": False,
        "refresh_cadence": "manual",
        "partition_strategy": "source/snapshot/accession",
    },
    "string": {
        "license_scope": "internal_only",
        "redistributable": False,
        "public_export_allowed": False,
        "refresh_cadence": "monthly",
        "partition_strategy": "source/snapshot/protein_pair",
    },
    "mega_motif_base": {
        "license_scope": "internal_only",
        "redistributable": False,
        "public_export_allowed": False,
        "refresh_cadence": "manual",
        "partition_strategy": "source/snapshot/accession",
    },
    "motivated_proteins": {
        "license_scope": "internal_only",
        "redistributable": False,
        "public_export_allowed": False,
        "refresh_cadence": "manual",
        "partition_strategy": "source/snapshot/accession",
    },
}


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


def _read_json_if_exists(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    if not isinstance(payload, Mapping):
        return {}
    return dict(payload)


def _rows_from_preview(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    return [dict(row) for row in payload.get("rows") or () if isinstance(row, Mapping)]


def _record_rows(library_path: Path | None) -> list[dict[str, Any]]:
    library = load_summary_library(library_path)
    if library is None:
        return []
    return [record.to_dict() for record in library.records]


def _merge_primary_records(*record_sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_summary_ids: set[str] = set()
    for record_set in record_sets:
        for row in record_set:
            summary_id = _clean_text(row.get("summary_id"))
            if not summary_id or summary_id in seen_summary_ids:
                continue
            seen_summary_ids.add(summary_id)
            merged.append(dict(row))
    return merged


def _build_pdb_entries(structure_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_entry: dict[str, dict[str, Any]] = {}
    for row in structure_rows:
        structure_source = _clean_text(row.get("structure_source"))
        structure_id = _clean_text(row.get("structure_id"))
        if not structure_source or not structure_id:
            continue
        entry_id = f"pdb_entry:{structure_source}:{structure_id}"
        if entry_id in by_entry:
            continue
        by_entry[entry_id] = {
            "entry_id": entry_id,
            "structure_source": structure_source,
            "structure_id": structure_id,
            "experimental_or_predicted": row.get("experimental_or_predicted"),
            "structure_kind": row.get("structure_kind"),
            "protein_refs": sorted(
                {
                    _clean_text(candidate.get("protein_ref"))
                    for candidate in structure_rows
                    if _clean_text(candidate.get("structure_source")) == structure_source
                    and _clean_text(candidate.get("structure_id")) == structure_id
                    and _clean_text(candidate.get("protein_ref"))
                }
            ),
        }
    return sorted(by_entry.values(), key=lambda row: row["entry_id"])


def _flatten_annotation_rows(
    record_rows: list[dict[str, Any]],
    *,
    kinds: tuple[str, ...],
    family_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in record_rows:
        context = record.get("context") or {}
        if not isinstance(context, Mapping):
            continue
        for bucket in (
            ("motif", "motif_references"),
            ("domain", "domain_references"),
            ("pathway", "pathway_references"),
        ):
            annotation_kind, key = bucket
            if annotation_kind not in kinds:
                continue
            for item in context.get(key) or ():
                if not isinstance(item, Mapping):
                    continue
                rows.append(
                    {
                        "annotation_id": (
                            f"{family_name}:{record.get('summary_id')}:{annotation_kind}:"
                            f"{item.get('namespace')}:{item.get('identifier')}"
                        ),
                        "owner_summary_id": record.get("summary_id"),
                        "owner_record_type": record.get("record_type"),
                        "annotation_kind": annotation_kind,
                        "namespace": item.get("namespace"),
                        "identifier": item.get("identifier"),
                        "label": item.get("label"),
                        "join_status": item.get("join_status"),
                        "source_name": item.get("source_name"),
                        "source_record_id": item.get("source_record_id"),
                        "span_start": item.get("span_start"),
                        "span_end": item.get("span_end"),
                        "notes": item.get("notes") or [],
                    }
                )
    return rows


def _flatten_provenance_rows(record_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in record_rows:
        context = record.get("context") or {}
        if not isinstance(context, Mapping):
            continue
        for item in context.get("provenance_pointers") or ():
            if not isinstance(item, Mapping):
                continue
            rows.append(
                {
                    "claim_id": f"{record.get('summary_id')}:{item.get('provenance_id')}",
                    "owner_summary_id": record.get("summary_id"),
                    "owner_record_type": record.get("record_type"),
                    "provenance_id": item.get("provenance_id"),
                    "source_name": item.get("source_name"),
                    "source_record_id": item.get("source_record_id"),
                    "release_version": item.get("release_version"),
                    "release_date": item.get("release_date"),
                    "acquired_at": item.get("acquired_at"),
                    "checksum": item.get("checksum"),
                    "join_status": item.get("join_status"),
                    "notes": item.get("notes") or [],
                }
            )
    return rows


def _flatten_materialization_routes(record_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in record_rows:
        context = record.get("context") or {}
        if not isinstance(context, Mapping):
            continue
        route_id_prefix = record.get("summary_id")
        for index, item in enumerate(context.get("materialization_pointers") or (), start=1):
            if not isinstance(item, Mapping):
                continue
            rows.append(
                {
                    "route_id": f"{route_id_prefix}:route:{index}",
                    "owner_summary_id": record.get("summary_id"),
                    "owner_record_type": record.get("record_type"),
                    "materialization_kind": item.get("materialization_kind"),
                    "pointer": item.get("pointer"),
                    "selector": item.get("selector"),
                    "source_name": item.get("source_name"),
                    "source_record_id": item.get("source_record_id"),
                    "notes": item.get("notes") or [],
                }
            )
        if context.get("deferred_payloads") or context.get("planning_index_keys"):
            rows.append(
                {
                    "route_id": f"{route_id_prefix}:route:summary_defaults",
                    "owner_summary_id": record.get("summary_id"),
                    "owner_record_type": record.get("record_type"),
                    "materialization_kind": "summary_defaults",
                    "pointer": ",".join(context.get("deferred_payloads") or []),
                    "selector": ",".join(context.get("planning_index_keys") or []),
                    "source_name": None,
                    "source_record_id": None,
                    "notes": list(context.get("lazy_loading_guidance") or []),
                }
            )
    return rows


def _build_similarity_rows(
    *,
    protein_similarity_path: Path | None,
    structure_similarity_path: Path | None,
    ligand_similarity_path: Path | None,
    interaction_similarity_path: Path | None,
) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    preview_specs = (
        ("protein", protein_similarity_path),
        ("structure", structure_similarity_path),
        ("ligand", ligand_similarity_path),
        ("interaction", interaction_similarity_path),
    )
    for signature_kind, path in preview_specs:
        for row in _rows_from_preview(_read_json_if_exists(path)):
            normalized = dict(row)
            normalized["signature_kind"] = signature_kind
            normalized["source_artifact"] = str(path).replace("\\", "/") if path else None
            combined.append(normalized)
    return combined


def _build_export_policy(source_descriptors: tuple[Any, ...]) -> dict[str, Any]:
    public_sources = [
        descriptor.source_name
        for descriptor in source_descriptors
        if descriptor.public_export_allowed
    ]
    internal_only_sources = [
        descriptor.source_name
        for descriptor in source_descriptors
        if not descriptor.public_export_allowed
    ]
    return {
        "public_bundle_mode": "metadata_only",
        "promotion_policy": "promoted_only",
        "default_reader_view": "best_evidence",
        "parallel_truth_surfaces": [
            "raw_claims",
            "derived_claims",
            "scraped_claims",
            "best_evidence_claims",
            "conflict_summary",
        ],
        "warning_banner": (
            "Public export omits full internal detail and raw corpora. Use the local warehouse "
            "for full-fidelity validation, enrichment, and packet hydration."
        ),
        "public_export_allowed_sources": public_sources,
        "internal_only_sources": internal_only_sources,
        "automatic_field_filtering": True,
        "github_release_asset_limit_bytes": 2 * 1024 * 1024 * 1024,
    }


def rebuild_library(
    *,
    warehouse_root: Path,
    warehouse_manifest_path: Path,
    warehouse_catalog_path: Path,
    warehouse_summary_path: Path,
    protein_library_path: Path | None,
    variant_library_path: Path | None,
    structure_library_path: Path | None,
    intact_library_path: Path | None,
    reactome_library_path: Path | None,
    ligand_rows_path: Path | None,
    protein_similarity_path: Path | None,
    structure_similarity_path: Path | None,
    ligand_similarity_path: Path | None,
    interaction_similarity_path: Path | None,
    leakage_groups_path: Path | None,
    source_coverage_path: Path | None,
    canonical_latest_path: Path | None,
) -> dict[str, Any]:
    warehouse_root.mkdir(parents=True, exist_ok=True)

    protein_rows = _merge_primary_records(
        _record_rows(protein_library_path),
        _record_rows(reactome_library_path),
        _record_rows(intact_library_path),
    )
    variant_rows = _record_rows(variant_library_path)
    structure_rows = _record_rows(structure_library_path)
    intact_rows = _record_rows(intact_library_path)
    reactome_rows = _record_rows(reactome_library_path)
    ligand_rows = _rows_from_preview(_read_json_if_exists(ligand_rows_path))
    source_coverage = _read_json_if_exists(source_coverage_path)
    canonical_latest = _read_json_if_exists(canonical_latest_path)

    protein_pair_rows = [
        row for row in intact_rows if _clean_text(row.get("record_type")) == "protein_protein"
    ]
    pathway_rows = _flatten_annotation_rows(
        reactome_rows,
        kinds=("pathway",),
        family_name="pathway_roles",
    )
    motif_rows = _flatten_annotation_rows(
        [*protein_rows, *variant_rows, *structure_rows],
        kinds=("motif", "domain"),
        family_name="motif_domain_site_annotations",
    )
    provenance_rows = _flatten_provenance_rows(
        [*protein_rows, *variant_rows, *structure_rows, *protein_pair_rows]
    )
    materialization_rows = _flatten_materialization_routes(
        [*protein_rows, *variant_rows, *structure_rows, *protein_pair_rows]
    )
    pdb_entry_rows = _build_pdb_entries(structure_rows)
    similarity_rows = _build_similarity_rows(
        protein_similarity_path=protein_similarity_path,
        structure_similarity_path=structure_similarity_path,
        ligand_similarity_path=ligand_similarity_path,
        interaction_similarity_path=interaction_similarity_path,
    )
    leakage_rows = _rows_from_preview(_read_json_if_exists(leakage_groups_path))

    family_rows: dict[str, list[dict[str, Any]]] = {
        "proteins": protein_rows,
        "protein_variants": variant_rows,
        "pdb_entries": pdb_entry_rows,
        "structure_units": structure_rows,
        "ligands": ligand_rows,
        "protein_ligand_edges": [dict(row) for row in ligand_rows],
        "protein_protein_edges": protein_pair_rows,
        "motif_domain_site_annotations": motif_rows,
        "pathway_roles": pathway_rows,
        "provenance_claims": provenance_rows,
        "materialization_routes": materialization_rows,
        "leakage_groups": leakage_rows,
        "similarity_signatures": similarity_rows,
    }

    snapshot_id = _clean_text(canonical_latest.get("run_id")) or "current"
    family_definitions: list[ReferenceWarehouseEntityFamily] = []
    all_warnings: list[str] = []
    for family_name, rows in family_rows.items():
        partition_path, storage_format, warnings = write_partition_rows(
            warehouse_root,
            family_name,
            snapshot_id=snapshot_id,
            rows=rows,
        )
        all_warnings.extend(warnings)
        family_definitions.append(
            ReferenceWarehouseEntityFamily(
                family_name=family_name,
                storage_format=storage_format,
                row_count=len(rows),
                partition_glob=str(partition_path).replace("\\", "/"),
                partition_keys=("snapshot_id",),
                public_export_allowed=family_name
                in {
                    "proteins",
                    "protein_variants",
                    "pdb_entries",
                    "structure_units",
                    "motif_domain_site_annotations",
                    "pathway_roles",
                    "leakage_groups",
                    "similarity_signatures",
                },
                export_policy="metadata_only",
                truth_surface_fields=(
                    "raw_claims",
                    "derived_claims",
                    "scraped_claims",
                    "best_evidence_claims",
                    "conflict_summary",
                ),
                default_view="best_evidence",
                notes=tuple(warnings),
            )
        )

    source_descriptors = build_source_descriptors_from_coverage(
        source_coverage,
        source_overrides=SOURCE_OVERRIDES,
    )
    priority_sources = {"string", "mega_motif_base", "motivated_proteins", "elm", "sabio_rk"}
    surfaced_priority_sources = {
        descriptor.source_key.casefold()
        for descriptor in source_descriptors
        if descriptor.source_key.casefold() in priority_sources
    }
    missing_priority_sources = sorted(priority_sources - surfaced_priority_sources)
    if missing_priority_sources:
        all_warnings.append(
            "missing priority sources in source coverage surface: "
            + ", ".join(missing_priority_sources)
        )

    validation_checks = {
        "canonical_record_counts": canonical_latest.get("record_counts") or {},
        "warehouse_family_counts": {
            family.family_name: family.row_count for family in family_definitions
        },
        "source_surface_counts": (source_coverage.get("summary") or {}).get("status_counts") or {},
        "priority_sources_visible": sorted(surfaced_priority_sources),
        "missing_priority_sources": missing_priority_sources,
    }
    validation_state = "warning" if all_warnings else "passed"
    validation = ReferenceWarehouseValidation(
        state=validation_state,
        validated_at=None,
        validator_id="scripts.rebuild_library",
        checks=validation_checks,
        warnings=tuple(all_warnings),
        errors=(),
    )
    export_policy = _build_export_policy(source_descriptors)

    provisional_manifest = build_manifest(
        warehouse_root=warehouse_root,
        catalog_path=warehouse_catalog_path,
        catalog_status="building",
        source_descriptors=source_descriptors,
        entity_families=tuple(family_definitions),
        validation=validation,
        export_policy=export_policy,
        warnings=all_warnings,
    )
    catalog_status, catalog_warnings = build_catalog(
        warehouse_catalog_path,
        manifest=provisional_manifest,
        partition_rows=family_rows,
    )
    all_warnings.extend(catalog_warnings)
    final_validation_state = "warning" if all_warnings else "passed"
    final_validation = ReferenceWarehouseValidation(
        state=final_validation_state,
        validated_at=None,
        validator_id="scripts.rebuild_library",
        checks=validation_checks,
        warnings=tuple(dict.fromkeys(all_warnings)),
        errors=(),
    )
    manifest = build_manifest(
        warehouse_root=warehouse_root,
        catalog_path=warehouse_catalog_path,
        catalog_status=catalog_status,
        source_descriptors=source_descriptors,
        entity_families=tuple(family_definitions),
        validation=final_validation,
        export_policy=export_policy,
        warnings=all_warnings,
    )
    write_json(warehouse_manifest_path, manifest.to_dict())
    catalog_metadata_sync_status, catalog_metadata_sync_warnings = sync_catalog_metadata(
        warehouse_catalog_path,
        manifest=manifest,
    )
    all_warnings.extend(catalog_metadata_sync_warnings)

    summary = {
        "artifact_id": "reference_warehouse_summary",
        "status": final_validation.state,
        "warehouse_root": str(warehouse_root).replace("\\", "/"),
        "warehouse_manifest_path": str(warehouse_manifest_path).replace("\\", "/"),
        "catalog_path": str(warehouse_catalog_path).replace("\\", "/"),
        "catalog_status": catalog_status,
        "family_counts": {
            family.family_name: family.row_count for family in manifest.entity_families
        },
        "source_count": manifest.source_count,
        "public_export_allowed_family_count": sum(
            1 for family in manifest.entity_families if family.public_export_allowed
        ),
        "default_view": "best_evidence",
        "truth_surface_fields": [
            "raw_claims",
            "derived_claims",
            "scraped_claims",
            "best_evidence_claims",
            "conflict_summary",
        ],
        "priority_source_status_counts": dict(
            Counter(
                descriptor.availability_status
                for descriptor in manifest.source_descriptors
                if descriptor.source_key.casefold() in priority_sources
            )
        ),
        "location_verified_source_count": sum(
            1 for descriptor in manifest.source_descriptors if descriptor.location_verified
        ),
        "scope_tier_counts": dict(
            Counter(descriptor.scope_tier for descriptor in manifest.source_descriptors)
        ),
        "warnings": list(manifest.warnings),
        "catalog_metadata_sync_status": catalog_metadata_sync_status,
    }
    write_json(warehouse_summary_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild the local ProteoSphere reference warehouse from pinned artifacts."
    )
    parser.add_argument("--warehouse-root", type=Path, default=DEFAULT_WAREHOUSE_ROOT)
    parser.add_argument("--warehouse-manifest", type=Path, default=DEFAULT_WAREHOUSE_MANIFEST)
    parser.add_argument("--warehouse-catalog", type=Path, default=DEFAULT_WAREHOUSE_CATALOG)
    parser.add_argument("--warehouse-summary", type=Path, default=DEFAULT_WAREHOUSE_SUMMARY)
    parser.add_argument("--protein-library", type=Path, default=DEFAULT_PROTEIN_LIBRARY)
    parser.add_argument("--variant-library", type=Path, default=DEFAULT_VARIANT_LIBRARY)
    parser.add_argument("--structure-library", type=Path, default=DEFAULT_STRUCTURE_LIBRARY)
    parser.add_argument("--intact-library", type=Path, default=DEFAULT_INTACT_LIBRARY)
    parser.add_argument("--reactome-library", type=Path, default=DEFAULT_REACTOME_LIBRARY)
    parser.add_argument("--ligand-rows", type=Path, default=DEFAULT_LIGAND_ROWS)
    parser.add_argument("--protein-similarity", type=Path, default=DEFAULT_PROTEIN_SIMILARITY)
    parser.add_argument("--structure-similarity", type=Path, default=DEFAULT_STRUCTURE_SIMILARITY)
    parser.add_argument("--ligand-similarity", type=Path, default=DEFAULT_LIGAND_SIMILARITY)
    parser.add_argument(
        "--interaction-similarity",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY,
    )
    parser.add_argument("--leakage-groups", type=Path, default=DEFAULT_LEAKAGE_GROUPS)
    parser.add_argument("--source-coverage", type=Path, default=DEFAULT_SOURCE_COVERAGE)
    parser.add_argument("--canonical-latest", type=Path, default=DEFAULT_CANONICAL_LATEST)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = rebuild_library(
        warehouse_root=args.warehouse_root,
        warehouse_manifest_path=args.warehouse_manifest,
        warehouse_catalog_path=args.warehouse_catalog,
        warehouse_summary_path=args.warehouse_summary,
        protein_library_path=args.protein_library,
        variant_library_path=args.variant_library,
        structure_library_path=args.structure_library,
        intact_library_path=args.intact_library,
        reactome_library_path=args.reactome_library,
        ligand_rows_path=args.ligand_rows,
        protein_similarity_path=args.protein_similarity,
        structure_similarity_path=args.structure_similarity,
        ligand_similarity_path=args.ligand_similarity,
        interaction_similarity_path=args.interaction_similarity,
        leakage_groups_path=args.leakage_groups,
        source_coverage_path=args.source_coverage,
        canonical_latest_path=args.canonical_latest,
    )
    print(args.warehouse_manifest)
    print(args.warehouse_summary)
    print(payload["status"])


if __name__ == "__main__":
    main()
