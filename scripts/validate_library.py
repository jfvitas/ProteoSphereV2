from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.reference_warehouse_common import (
    DEFAULT_WAREHOUSE_MANIFEST,
    load_reference_warehouse_manifest,
    read_json,
    write_json,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "reference_library_validation.json"
DEFAULT_RELEASE_SUMMARY = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
DEFAULT_RELEASE_BUNDLE = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
PRIORITY_SOURCES = {"string", "mega_motif_base", "motivated_proteins", "elm", "sabio_rk"}
REQUIRED_CLAIM_SURFACE_COLUMNS = {
    "raw_claims",
    "derived_claims",
    "scraped_claims",
    "best_evidence_claims",
    "conflict_summary",
}


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    if isinstance(payload, dict):
        return payload
    return {}


def validate_library(
    *,
    warehouse_manifest_path: Path,
    output_path: Path,
    release_summary_path: Path,
    release_bundle_path: Path,
) -> dict[str, Any]:
    manifest = load_reference_warehouse_manifest(warehouse_manifest_path)
    catalog_path = Path(manifest.catalog_path)
    catalog_payload: dict[str, Any] = {}
    if catalog_path.exists():
        try:
            import duckdb  # type: ignore[import-not-found]

            with duckdb.connect(str(catalog_path), read_only=True) as connection:
                metadata_row = connection.sql(
                    "select warehouse_root, catalog_path, catalog_status, family_count, source_count from warehouse_metadata limit 1"
                ).fetchone()
                if metadata_row:
                    catalog_payload["warehouse_metadata"] = {
                        "warehouse_root": metadata_row[0],
                        "catalog_path": metadata_row[1],
                        "catalog_status": metadata_row[2],
                        "family_count": int(metadata_row[3] or 0),
                        "source_count": int(metadata_row[4] or 0),
                    }
                catalog_payload["protein_protein_edges"] = {
                    "total_edges": int(
                        connection.sql("select count(*) from protein_protein_edges").fetchone()[0]
                    ),
                    "edges_with_null_endpoint": int(
                        connection.sql(
                            """
                            select count(*)
                            from protein_protein_edges
                            where protein_a_ref is null or protein_b_ref is null
                            """
                        ).fetchone()[0]
                    ),
                    "edges_with_unresolved_protein_ref": int(
                        connection.sql(
                            """
                            select count(*)
                            from protein_protein_edges p
                            left join proteins a on p.protein_a_ref = a.protein_ref
                            left join proteins b on p.protein_b_ref = b.protein_ref
                            where (p.protein_a_ref is not null and a.protein_ref is null)
                               or (p.protein_b_ref is not null and b.protein_ref is null)
                            """
                        ).fetchone()[0]
                    ),
                }
                catalog_payload["protein_ligand_edges"] = {
                    "total_edges": int(
                        connection.sql("select count(*) from protein_ligand_edges").fetchone()[0]
                    ),
                    "edges_with_null_endpoint": int(
                        connection.sql(
                            """
                            select count(*)
                            from protein_ligand_edges
                            where protein_ref is null or ligand_ref is null
                            """
                        ).fetchone()[0]
                    ),
                    "edges_with_unresolved_entity_ref": int(
                        connection.sql(
                            """
                            select count(*)
                            from protein_ligand_edges e
                            left join proteins p on e.protein_ref = p.protein_ref
                            left join ligands l on e.ligand_ref = l.ligand_ref
                            where (e.protein_ref is not null and p.protein_ref is null)
                               or (e.ligand_ref is not null and l.ligand_ref is null)
                            """
                        ).fetchone()[0]
                    ),
                    "edges_with_unknown_ligand_ref": int(
                        connection.sql(
                            "select count(*) from protein_ligand_edges where ligand_ref = 'UNKNOWN'"
                        ).fetchone()[0]
                    ),
                }
                catalog_payload["materialization_routes"] = {
                    "total_routes": int(
                        connection.sql("select count(*) from materialization_routes").fetchone()[0]
                    ),
                    "library_asset_pack_routes": int(
                        connection.sql(
                            """
                            select count(*)
                            from materialization_routes
                            where pointer ilike 'D:/ProteoSphere/reference_library/asset_packs/%'
                            """
                        ).fetchone()[0]
                    ),
                    "library_owned_pointer_routes": int(
                        connection.sql(
                            """
                            select count(*)
                            from materialization_routes
                            where pointer ilike 'D:/ProteoSphere/reference_library/%'
                               or pointer ilike 'E:/ProteoSphere/reference_library/%'
                            """
                        ).fetchone()[0]
                    ),
                    "foreign_pointer_routes": int(
                        connection.sql(
                            """
                            select count(*)
                            from materialization_routes
                            where (pointer ilike 'C:%' or pointer ilike 'D:%' or pointer ilike 'E:%')
                              and pointer not ilike 'D:/ProteoSphere/reference_library/%'
                              and pointer not ilike 'E:/ProteoSphere/reference_library/%'
                            """
                        ).fetchone()[0]
                    ),
                    "bio_agent_lab_pointer_routes": int(
                        connection.sql(
                            """
                            select count(*)
                            from materialization_routes
                            where pointer ilike 'C:%bio-agent-lab%'
                               or pointer ilike 'D:%bio-agent-lab%'
                            """
                        ).fetchone()[0]
                    ),
                }
        except Exception as exc:
            catalog_payload["catalog_error"] = str(exc)
    family_checks: list[dict[str, Any]] = []
    missing_family_partitions: list[str] = []
    truth_surface_issues: list[str] = []
    for family in manifest.entity_families:
        partition_path = Path(family.partition_glob)
        exists = partition_path.exists()
        truth_surface_fields = list(family.truth_surface_fields)
        actual_columns: list[str] = []
        claim_surface_materialized = False
        if catalog_path.exists() and "catalog_error" not in catalog_payload:
            try:
                import duckdb  # type: ignore[import-not-found]

                with duckdb.connect(str(catalog_path), read_only=True) as connection:
                    actual_columns = [
                        row[0]
                        for row in connection.sql(f"describe {family.family_name}").fetchall()
                    ]
            except Exception:
                actual_columns = []
        claim_surface_materialized = REQUIRED_CLAIM_SURFACE_COLUMNS.issubset(set(actual_columns))
        truth_surface_ok = bool(exists)
        family_checks.append(
            {
                "family_name": family.family_name,
                "row_count": family.row_count,
                "partition_path": str(partition_path).replace("\\", "/"),
                "present": exists,
                "storage_format": family.storage_format,
                "truth_surface_fields": truth_surface_fields,
                "default_view": family.default_view,
                "truth_surface_ok": truth_surface_ok,
                "physical_columns": actual_columns,
                "claim_surface_materialized": claim_surface_materialized,
                "storage_contract": (
                    "claim_surfaces_materialized"
                    if claim_surface_materialized
                    else "summary_backed_reference_record"
                ),
            }
        )
        if not exists:
            missing_family_partitions.append(family.family_name)

    source_descriptor_issues: list[str] = []
    location_validation: list[dict[str, Any]] = []
    priority_surface = {
        descriptor.source_key.casefold(): descriptor.availability_status
        for descriptor in manifest.source_descriptors
        if descriptor.source_key.casefold() in PRIORITY_SOURCES
    }
    for descriptor in manifest.source_descriptors:
        if not descriptor.license_scope:
            source_descriptor_issues.append(f"missing license_scope for {descriptor.source_key}")
        if descriptor.public_export_allowed and descriptor.license_scope == "internal_only":
            source_descriptor_issues.append(
                f"inconsistent export policy for {descriptor.source_key}: "
                "internal_only cannot be public_export_allowed"
            )
        location_ok = descriptor.location_verified and bool(
            descriptor.canonical_root or descriptor.source_locator
        )
        location_validation.append(
            {
                "source_key": descriptor.source_key,
                "location_verified": descriptor.location_verified,
                "canonical_root": descriptor.canonical_root,
                "consolidation_status": descriptor.consolidation_status,
                "scope_tier": descriptor.scope_tier,
                "location_ok": location_ok,
            }
        )
        if not location_ok and descriptor.availability_status in {"present", "partial"}:
            location_validation[-1]["warning"] = (
                f"location verification incomplete for {descriptor.source_key}"
            )
    missing_priority_sources = sorted(PRIORITY_SOURCES - set(priority_surface))
    if missing_priority_sources:
        source_descriptor_issues.append(
            "priority sources missing from warehouse manifest: "
            + ", ".join(missing_priority_sources)
        )
    uniparc_present = any(
        descriptor.source_key.casefold() == "uniparc" for descriptor in manifest.source_descriptors
    )
    uniparc_blocker = {
        "source_key": "uniparc",
        "located": uniparc_present,
        "status": "present" if uniparc_present else "blocked_missing",
    }

    release_summary = _read_json_if_exists(release_summary_path)
    release_bundle = _read_json_if_exists(release_bundle_path)
    release_consistency = {
        "summary_status": release_summary.get("status"),
        "bundle_status": release_bundle.get("status"),
        "bundle_status_allowed": release_bundle.get("status")
        in (release_bundle.get("truth_boundary") or {}).get("allowed_statuses", []),
        "runtime_surface": (release_summary.get("execution_scope") or {}).get("runtime_surface"),
    }
    release_consistency_ok = bool(release_bundle) and release_consistency["bundle_status_allowed"]

    errors = []
    if missing_family_partitions:
        errors.append(
            "missing family partition files: " + ", ".join(sorted(missing_family_partitions))
        )
    if source_descriptor_issues:
        errors.extend(source_descriptor_issues)
    if not release_consistency_ok:
        errors.append("release summary and release bundle manifest are not self-consistent")
    metadata_consistency = {
        "catalog_present": catalog_path.exists(),
        "catalog_error": catalog_payload.get("catalog_error"),
        "warehouse_root_matches_manifest": (
            (catalog_payload.get("warehouse_metadata") or {}).get("warehouse_root")
            == manifest.warehouse_root
            if catalog_payload.get("warehouse_metadata")
            else None
        ),
        "catalog_path_matches_manifest": (
            (catalog_payload.get("warehouse_metadata") or {}).get("catalog_path")
            == manifest.catalog_path
            if catalog_payload.get("warehouse_metadata")
            else None
        ),
        "catalog_status_matches_manifest": (
            (catalog_payload.get("warehouse_metadata") or {}).get("catalog_status")
            == manifest.catalog_status
            if catalog_payload.get("warehouse_metadata")
            else None
        ),
        "family_count_matches_manifest": (
            (catalog_payload.get("warehouse_metadata") or {}).get("family_count")
            == manifest.family_count
            if catalog_payload.get("warehouse_metadata")
            else None
        ),
        "source_count_matches_manifest": (
            (catalog_payload.get("warehouse_metadata") or {}).get("source_count")
            == manifest.source_count
            if catalog_payload.get("warehouse_metadata")
            else None
        ),
    }
    if catalog_payload.get("catalog_error"):
        errors.append("catalog diagnostics failed to load")
    elif catalog_payload.get("warehouse_metadata"):
        for key in (
            "warehouse_root_matches_manifest",
            "catalog_path_matches_manifest",
            "catalog_status_matches_manifest",
            "family_count_matches_manifest",
            "source_count_matches_manifest",
        ):
            if metadata_consistency.get(key) is False:
                errors.append(f"catalog metadata mismatch: {key}")

    warnings = list(manifest.warnings)
    warnings.extend(
        row["warning"]
        for row in location_validation
        if isinstance(row.get("warning"), str) and row["warning"]
    )
    if not uniparc_present:
        warnings.append(
            "uniparc remains an explicit blocker until physically located or marked unavailable with evidence"
        )
    if truth_surface_issues:
        warnings.extend(truth_surface_issues)
    if catalog_payload.get("protein_protein_edges", {}).get("edges_with_unresolved_protein_ref", 0):
        warnings.append(
            "protein_protein_edges includes unresolved protein references; use as summarized graph evidence, not lossless graph truth"
        )
    if catalog_payload.get("protein_ligand_edges", {}).get("edges_with_unresolved_entity_ref", 0):
        warnings.append(
            "protein_ligand_edges includes unresolved protein or ligand references; UNKNOWN ligand placeholders remain in the condensed store"
        )
    if catalog_payload.get("materialization_routes", {}).get("bio_agent_lab_pointer_routes", 0):
        warnings.append(
            "materialization_routes still contain direct bio-agent-lab pointers; resolve heavy assets through the source registry instead of direct path use"
        )
    if catalog_payload.get("materialization_routes", {}).get("foreign_pointer_routes", 0):
        warnings.append(
            "materialization_routes still contain foreign filesystem pointers outside the library-owned archive roots"
        )
    status = "passed" if not errors else "failed"
    payload = {
        "artifact_id": "reference_library_validation",
        "schema_id": "proteosphere-reference-library-validation-2026-04-10",
        "status": status,
        "warehouse_manifest_path": str(warehouse_manifest_path).replace("\\", "/"),
        "checks": {
            "family_checks": family_checks,
            "priority_source_surface": priority_surface,
            "location_validation": location_validation,
            "truth_surface_validation": {
                "families_checked": len(family_checks),
                "families_with_claim_surface_materialization": sum(
                    1 for row in family_checks if row["claim_surface_materialized"]
                ),
                "families_using_summary_contract": sum(
                    1
                    for row in family_checks
                    if row["storage_contract"] == "summary_backed_reference_record"
                ),
                "contract": "summary_backed_reference_warehouse",
            },
            "uniparc_blocker": uniparc_blocker,
            "release_consistency": release_consistency,
            "metadata_consistency": metadata_consistency,
            "connectivity_validation": {
                "protein_protein_edges": catalog_payload.get("protein_protein_edges") or {},
                "protein_ligand_edges": catalog_payload.get("protein_ligand_edges") or {},
            },
            "materialization_validation": catalog_payload.get("materialization_routes") or {},
        },
        "errors": errors,
        "warnings": warnings,
    }
    write_json(output_path, payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the rebuilt reference warehouse.")
    parser.add_argument("--warehouse-manifest", type=Path, default=DEFAULT_WAREHOUSE_MANIFEST)
    parser.add_argument("--release-summary", type=Path, default=DEFAULT_RELEASE_SUMMARY)
    parser.add_argument("--release-bundle", type=Path, default=DEFAULT_RELEASE_BUNDLE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = validate_library(
        warehouse_manifest_path=args.warehouse_manifest,
        output_path=args.output,
        release_summary_path=args.release_summary,
        release_bundle_path=args.release_bundle,
    )
    print(args.output)
    if payload["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
