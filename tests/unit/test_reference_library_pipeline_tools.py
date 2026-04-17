from __future__ import annotations

import json
from pathlib import Path

import duckdb  # type: ignore[import-not-found]

from scripts.augment_runtime_connectivity import augment_runtime_connectivity
from scripts.execute_widened_scope_consolidation import execute_widened_scope_consolidation
from scripts.export_public_library import export_public_library
from scripts.import_existing_scraped_data import import_existing_scraped_data
from scripts.internalize_materialization_routes import internalize_materialization_routes
from scripts.materialize_library_asset_pack import materialize_library_asset_pack
from scripts.plan_widened_scope_consolidation import plan_widened_scope_consolidation
from scripts.relocate_runtime_library import _replace_runtime_path, relocate_runtime_library
from scripts.run_raw_disconnected_acceptance import run_raw_disconnected_acceptance
from scripts.run_targeted_page_scrape_capture import run_targeted_page_scrape_capture
from scripts.rebuild_library import (
    DEFAULT_CANONICAL_LATEST,
    DEFAULT_INTACT_LIBRARY,
    DEFAULT_INTERACTION_SIMILARITY,
    DEFAULT_LEAKAGE_GROUPS,
    DEFAULT_LIGAND_ROWS,
    DEFAULT_LIGAND_SIMILARITY,
    DEFAULT_PROTEIN_LIBRARY,
    DEFAULT_PROTEIN_SIMILARITY,
    DEFAULT_REACTOME_LIBRARY,
    DEFAULT_SOURCE_COVERAGE,
    DEFAULT_STRUCTURE_LIBRARY,
    DEFAULT_STRUCTURE_SIMILARITY,
    DEFAULT_VARIANT_LIBRARY,
    rebuild_library,
)
from scripts.refresh_sources import refresh_sources
from scripts.refresh_warehouse_source_descriptors import refresh_warehouse_source_descriptors
from scripts.validate_library import (
    DEFAULT_RELEASE_BUNDLE,
    DEFAULT_RELEASE_SUMMARY,
    validate_library,
)


def test_refresh_sources_writes_plan_and_snapshot_index(tmp_path: Path) -> None:
    raw_root = tmp_path / "data" / "raw"
    (raw_root / "uniprot" / "20260410T000000Z").mkdir(parents=True)
    (raw_root / "uniprot" / "20260410T000000Z" / "entry.json").write_text(
        "{}",
        encoding="utf-8",
    )

    output_path = tmp_path / "artifacts" / "status" / "source_refresh_plan.json"
    snapshot_index_path = tmp_path / "artifacts" / "status" / "source_snapshot_index.json"

    payload = refresh_sources(
        accessions=("P69905", "P68871"),
        raw_root=raw_root,
        output_path=output_path,
        snapshot_index_path=snapshot_index_path,
        sources=("uniprot", "string"),
        include_local_priority=False,
        execute_downloads=False,
    )

    saved_index = json.loads(snapshot_index_path.read_text(encoding="utf-8"))
    assert payload["status"] == "planned"
    assert output_path.exists()
    assert snapshot_index_path.exists()
    assert payload["refresh_plan"]["sources"] == ["uniprot", "string"]
    assert saved_index["summary"]["present_sources"] == ["uniprot"]
    assert saved_index["summary"]["missing_sources"] == ["string"]


def _rebuild_into(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    warehouse_root = tmp_path / "warehouse"
    warehouse_manifest = warehouse_root / "warehouse_manifest.json"
    warehouse_catalog = warehouse_root / "catalog" / "reference_library.duckdb"
    warehouse_summary = warehouse_root / "warehouse_summary.json"
    payload = rebuild_library(
        warehouse_root=warehouse_root,
        warehouse_manifest_path=warehouse_manifest,
        warehouse_catalog_path=warehouse_catalog,
        warehouse_summary_path=warehouse_summary,
        protein_library_path=DEFAULT_PROTEIN_LIBRARY,
        variant_library_path=DEFAULT_VARIANT_LIBRARY,
        structure_library_path=DEFAULT_STRUCTURE_LIBRARY,
        intact_library_path=DEFAULT_INTACT_LIBRARY,
        reactome_library_path=DEFAULT_REACTOME_LIBRARY,
        ligand_rows_path=DEFAULT_LIGAND_ROWS,
        protein_similarity_path=DEFAULT_PROTEIN_SIMILARITY,
        structure_similarity_path=DEFAULT_STRUCTURE_SIMILARITY,
        ligand_similarity_path=DEFAULT_LIGAND_SIMILARITY,
        interaction_similarity_path=DEFAULT_INTERACTION_SIMILARITY,
        leakage_groups_path=DEFAULT_LEAKAGE_GROUPS,
        source_coverage_path=DEFAULT_SOURCE_COVERAGE,
        canonical_latest_path=DEFAULT_CANONICAL_LATEST,
    )
    return warehouse_manifest, payload


def test_rebuild_library_creates_manifest_and_summary(tmp_path: Path) -> None:
    warehouse_manifest, payload = _rebuild_into(tmp_path)
    manifest_payload = json.loads(warehouse_manifest.read_text(encoding="utf-8"))

    assert payload["status"] in {"passed", "warning"}
    assert warehouse_manifest.exists()
    assert manifest_payload["family_count"] >= 10
    assert {
        family["family_name"] for family in manifest_payload["entity_families"]
    } >= {
        "proteins",
        "protein_variants",
        "pdb_entries",
        "structure_units",
        "ligands",
        "provenance_claims",
        "similarity_signatures",
    }


def test_validate_library_passes_for_rebuilt_manifest(tmp_path: Path) -> None:
    warehouse_manifest, _ = _rebuild_into(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "reference_library_validation.json"

    payload = validate_library(
        warehouse_manifest_path=warehouse_manifest,
        output_path=output_path,
        release_summary_path=DEFAULT_RELEASE_SUMMARY,
        release_bundle_path=DEFAULT_RELEASE_BUNDLE,
    )

    assert payload["status"] == "passed"
    assert output_path.exists()
    assert payload["checks"]["release_consistency"]["bundle_status_allowed"] is True
    assert payload["checks"]["truth_surface_validation"]["contract"] == "summary_backed_reference_warehouse"
    assert payload["checks"]["metadata_consistency"]["catalog_present"] is True
    assert "uniparc_blocker" in payload["checks"]


def test_export_public_library_writes_warning_and_manifest(tmp_path: Path) -> None:
    warehouse_manifest, _ = _rebuild_into(tmp_path)
    output_dir = tmp_path / "artifacts" / "bundles" / "public_metadata"
    public_manifest = output_dir / "public_reference_library_manifest.json"
    warning_path = output_dir / "WARNING.txt"
    validation_receipts_dir = tmp_path / "warehouse" / "control" / "validation_receipts"
    validation_receipts_dir.mkdir(parents=True)
    work_units_path = tmp_path / "warehouse" / "control" / "work_units.json"
    work_units_path.parent.mkdir(parents=True, exist_ok=True)
    work_units_path.write_text(json.dumps({"work_units": []}), encoding="utf-8")

    payload = export_public_library(
        warehouse_manifest_path=warehouse_manifest,
        output_dir=output_dir,
        public_manifest_path=public_manifest,
        warning_path=warning_path,
        validation_receipts_dir=validation_receipts_dir,
        work_units_path=work_units_path,
    )

    assert payload["status"] == "metadata_only_exported"
    assert public_manifest.exists()
    assert warning_path.exists()
    assert payload["public_bundle_size_bytes"] > 0
    assert payload["public_export_allowed_families"]
    assert "Public export omits full internal detail" in warning_path.read_text(encoding="utf-8")
    assert payload["metadata_only_bundle"] is True
    assert payload["promoted_only_source"] is True
    assert payload["default_reader_view"] == "best_evidence"
    assert payload["storage_contract"] == "summary_backed_reference_warehouse"
    assert payload["truth_surface_policy"]["claim_surface_materialization"] == "logical_only"


def test_export_public_library_blocks_promoted_public_work_without_receipt(tmp_path: Path) -> None:
    warehouse_manifest, _ = _rebuild_into(tmp_path)
    output_dir = tmp_path / "artifacts" / "bundles" / "public_metadata"
    public_manifest = output_dir / "public_reference_library_manifest.json"
    warning_path = output_dir / "WARNING.txt"
    validation_receipts_dir = tmp_path / "warehouse" / "control" / "validation_receipts"
    validation_receipts_dir.mkdir(parents=True, exist_ok=True)
    work_units_path = tmp_path / "warehouse" / "control" / "work_units.json"
    work_units_path.parent.mkdir(parents=True, exist_ok=True)
    work_units_path.write_text(
        json.dumps(
            {
                "work_units": [
                    {
                        "work_unit_id": "proteins:current:all",
                        "lane": "identity_sequence",
                        "source_family": "proteins",
                        "snapshot_id": "current",
                        "shard_key": "all",
                        "inputs": ["E:/ProteoSphere/reference_library/partitions/proteins"],
                        "expected_outputs": ["E:/ProteoSphere/reference_library/partitions/proteins"],
                        "status": "promoted",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        export_public_library(
            warehouse_manifest_path=warehouse_manifest,
            output_dir=output_dir,
            public_manifest_path=public_manifest,
            warning_path=warning_path,
            validation_receipts_dir=validation_receipts_dir,
            work_units_path=work_units_path,
        )
    except ValueError as exc:
        assert "lack passing validation receipts" in str(exc)
    else:
        raise AssertionError("expected export gating failure")


def test_refresh_warehouse_source_descriptors_updates_source_inventory(tmp_path: Path) -> None:
    warehouse_manifest, _ = _rebuild_into(tmp_path)
    warehouse_summary = tmp_path / "warehouse" / "warehouse_summary.json"
    raw_root = tmp_path / "data" / "raw"
    (raw_root / "mega_motif_base" / "20260411T175400Z").mkdir(parents=True)
    (raw_root / "mega_motif_base" / "20260411T175400Z" / "manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )

    payload = refresh_warehouse_source_descriptors(
        warehouse_manifest_path=warehouse_manifest,
        warehouse_summary_path=warehouse_summary,
        raw_root=raw_root,
    )

    saved_manifest = json.loads(warehouse_manifest.read_text(encoding="utf-8"))
    saved_summary = json.loads(warehouse_summary.read_text(encoding="utf-8"))
    assert payload["status"] == "refreshed"
    assert any(
        descriptor["source_key"] == "mega_motif_base"
        and descriptor["availability_status"] == "present"
        for descriptor in saved_manifest["source_descriptors"]
    )
    assert saved_summary["priority_source_status_counts"]["missing"] >= 0
    assert saved_summary["catalog_metadata_sync_status"] == "ready"


def test_refresh_warehouse_source_descriptors_promotes_registry_backed_string_surface(tmp_path: Path) -> None:
    warehouse_manifest, _ = _rebuild_into(tmp_path)
    warehouse_summary = tmp_path / "warehouse" / "warehouse_summary.json"
    raw_root = tmp_path / "data" / "raw"
    (raw_root / "protein_data_scope_seed" / "string").mkdir(parents=True)
    (raw_root / "protein_data_scope_seed" / "string" / "protein.links.txt").write_text(
        "9606.ENSP0001 9606.ENSP0002 999",
        encoding="utf-8",
    )
    source_registry = tmp_path / "warehouse" / "control" / "source_registry.json"
    source_registry.parent.mkdir(parents=True, exist_ok=True)
    source_registry.write_text(
        json.dumps(
            {
                "source_records": [
                    {
                        "source_id": "string:current",
                        "source_family": "string",
                        "snapshot_id": "current",
                        "root_paths": [str(raw_root / "protein_data_scope_seed" / "string")],
                        "authoritative_root": str(raw_root / "protein_data_scope_seed" / "string"),
                        "integration_status": "promoted",
                        "consolidation_status": "pending",
                        "scope_tier": "authoritative",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    refresh_warehouse_source_descriptors(
        warehouse_manifest_path=warehouse_manifest,
        warehouse_summary_path=warehouse_summary,
        raw_root=raw_root,
        source_registry_path=source_registry,
    )

    saved_manifest = json.loads(warehouse_manifest.read_text(encoding="utf-8"))
    string_row = next(
        descriptor for descriptor in saved_manifest["source_descriptors"] if descriptor["source_key"] == "string"
    )
    assert string_row["availability_status"] == "present"
    assert string_row["location_verified"] is True


def test_internalize_materialization_routes_rewrites_external_alphafold_pointers(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "warehouse"
    catalog_path = warehouse_root / "catalog" / "reference_library.duckdb"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    partition_path = (
        warehouse_root
        / "partitions"
        / "materialization_routes"
        / "snapshot_id=test"
        / "materialization_routes.parquet"
    )
    partition_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = warehouse_root / "warehouse_manifest.json"
    source_registry_path = warehouse_root / "control" / "source_registry.json"
    source_registry_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = warehouse_root / "control" / "materialization_internalization.latest.json"

    manifest_path.write_text(
        json.dumps(
            {
                "warehouse_root": str(warehouse_root).replace("\\", "/"),
                "catalog_path": str(catalog_path).replace("\\", "/"),
                "entity_families": [
                    {
                        "family_name": "materialization_routes",
                        "partition_glob": str(partition_path).replace("\\", "/"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source_registry_path.write_text(
        json.dumps(
            {
                "source_records": [
                    {
                        "source_id": "alphafold:current",
                        "source_family": "alphafold",
                        "snapshot_id": "current",
                        "authoritative_root": (
                            "E:/ProteoSphere/reference_library/incoming_mirrors/alphafold/current/alphafold_db"
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    import duckdb  # type: ignore[import-not-found]

    with duckdb.connect(str(catalog_path)) as connection:
        connection.execute(
            """
            create table materialization_routes (
                route_id varchar,
                owner_summary_id varchar,
                owner_record_type varchar,
                materialization_kind varchar,
                pointer varchar,
                selector varchar,
                source_name varchar,
                source_record_id varchar,
                snapshot_id varchar
            )
            """
        )
        connection.execute(
            """
            insert into materialization_routes values
            (
                'route-1',
                'protein:P69905',
                'protein',
                'archive_member',
                'C:/Users/jfvit/Documents/bio-agent-lab/data_sources/alphafold/swissprot_pdb_v6.tar',
                'AF-P69905-F1-model_v6.pdb.gz',
                'AlphaFold DB',
                'AFDB:P69905',
                'current'
            )
            """
        )

    payload = internalize_materialization_routes(
        warehouse_manifest_path=manifest_path,
        source_registry_path=source_registry_path,
        output_receipt_path=receipt_path,
    )

    assert payload["status"] == "internalized"
    assert payload["updated_count"] == 1
    assert payload["unresolved_count"] == 0
    assert receipt_path.exists()

    with duckdb.connect(str(catalog_path), read_only=True) as connection:
        row = connection.sql(
            """
            select
                pointer,
                selector,
                original_pointer,
                source_registry_anchor,
                resolution_mode,
                storage_contract,
                external_dependency_cleared
            from materialization_routes
            """
        ).fetchone()

    assert row is not None
    assert row[0] == "E:/ProteoSphere/reference_library/incoming_mirrors/alphafold/current/alphafold_db/swissprot_pdb_v6.tar"
    assert row[1] == "AF-P69905-F1-model_v6.pdb.gz"
    assert row[2] == "C:/Users/jfvit/Documents/bio-agent-lab/data_sources/alphafold/swissprot_pdb_v6.tar"
    assert row[3] == "E:/ProteoSphere/reference_library/incoming_mirrors/alphafold/current/alphafold_db"
    assert row[4] == "library_archive_member"
    assert row[5] == "library_owned_archive_member"
    assert row[6] is True
    assert partition_path.exists()


def test_augment_runtime_connectivity_backfills_missing_non_null_protein_refs(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "warehouse"
    catalog_path = warehouse_root / "catalog" / "reference_library.duckdb"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = warehouse_root / "warehouse_manifest.json"
    receipt_path = warehouse_root / "control" / "runtime_connectivity.latest.json"

    manifest_path.write_text(
        json.dumps(
            {
                "warehouse_id": "reference-warehouse:test",
                "warehouse_root": str(warehouse_root).replace("\\", "/"),
                "catalog_path": str(catalog_path).replace("\\", "/"),
                "catalog_engine": "duckdb",
                "catalog_status": "ready",
                "generated_at": "2026-04-12T00:00:00+00:00",
                "source_descriptors": [],
                "entity_families": [
                    {
                        "family_name": "proteins",
                        "storage_format": "parquet",
                        "row_count": 1,
                        "partition_glob": str(
                            warehouse_root
                            / "partitions"
                            / "proteins"
                            / "snapshot_id=test"
                            / "proteins.parquet"
                        ).replace("\\", "/"),
                        "partition_keys": ["snapshot_id"],
                        "public_export_allowed": True,
                        "export_policy": "metadata_only",
                        "truth_surface_fields": ["best_evidence_claims"],
                        "default_view": "best_evidence",
                        "notes": [],
                    }
                ],
                "validation": {
                    "state": "passed",
                    "validated_at": "2026-04-12T00:00:00+00:00",
                    "checks": {},
                    "warnings": [],
                    "errors": [],
                },
                "export_policy": {},
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )

    with duckdb.connect(str(catalog_path)) as connection:
        connection.execute(
            """
            create table warehouse_metadata (
                warehouse_id varchar,
                warehouse_root varchar,
                catalog_path varchar,
                catalog_engine varchar,
                catalog_status varchar,
                generated_at varchar,
                family_count bigint,
                source_count bigint
            )
            """
        )
        connection.execute(
            """
            insert into warehouse_metadata values
            (
                'reference-warehouse:test',
                ?, ?, 'duckdb', 'ready', '2026-04-12T00:00:00+00:00', 1, 0
            )
            """,
            [str(warehouse_root).replace("\\", "/"), str(catalog_path).replace("\\", "/")],
        )
        connection.execute("create table warehouse_sources as select * from (select 1 as placeholder) where 1=0")
        connection.execute(
            """
            create table warehouse_families (
                family_name varchar,
                storage_format varchar,
                row_count bigint,
                partition_glob varchar,
                partition_keys varchar[],
                public_export_allowed boolean,
                export_policy varchar,
                truth_surface_fields varchar[],
                default_view varchar,
                notes varchar[]
            )
            """
        )
        connection.execute(
            """
            insert into warehouse_families values
            (
                'proteins',
                'parquet',
                1,
                ?,
                ['snapshot_id'],
                true,
                'metadata_only',
                ['best_evidence_claims'],
                'best_evidence',
                []
            )
            """,
            [
                str(
                    warehouse_root
                    / "partitions"
                    / "proteins"
                    / "snapshot_id=test"
                    / "proteins.parquet"
                ).replace("\\", "/")
            ],
        )
        connection.execute(
            """
            create table proteins (
                accession varchar,
                protein_ref varchar,
                entry_name varchar,
                uniref100_cluster varchar,
                uniref90_cluster varchar,
                uniref50_cluster varchar,
                uniparc_id varchar,
                taxon_id bigint,
                accession_prefix1 varchar,
                accession_prefix2 varchar,
                snapshot_id varchar
            )
            """
        )
        connection.execute(
            """
            insert into proteins values
            ('P69905', 'protein:P69905', 'HBA_HUMAN', null, null, null, null, 9606, 'P', 'P6', 'seed')
            """
        )
        connection.execute(
            """
            create table protein_protein_edges (
                edge_id varchar,
                protein_a_ref varchar,
                protein_b_ref varchar,
                structure_id varchar,
                binding_measurement_raw varchar,
                reference_file varchar,
                commentary varchar,
                complex_type varchar,
                interaction_source varchar,
                pmid varchar,
                confidence_score integer,
                snapshot_id varchar
            )
            """
        )
        connection.execute(
            """
            insert into protein_protein_edges values
            ('edge-1', 'protein:P69905', 'protein:P69905-2', null, null, null, null, null, 'test', null, null, 'seed')
            """
        )
        connection.execute(
            """
            create table protein_ligand_edges (
                edge_id varchar,
                structure_id varchar,
                protein_ref varchar,
                ligand_ref varchar,
                binding_measurement_raw varchar,
                reference_file varchar,
                complex_type varchar,
                commentary varchar,
                snapshot_id varchar
            )
            """
        )

    payload = augment_runtime_connectivity(
        warehouse_manifest_path=manifest_path,
        output_receipt_path=receipt_path,
    )

    assert payload["status"] == "augmented"
    assert payload["placeholder_count"] == 1
    assert payload["placeholder_refs"] == ["protein:P69905-2"]
    assert receipt_path.exists()

    with duckdb.connect(str(catalog_path), read_only=True) as connection:
        placeholder_row = connection.sql(
            """
            select accession, protein_ref, accession_prefix1, accession_prefix2, snapshot_id
            from proteins
            where protein_ref = 'protein:P69905-2'
            """
        ).fetchone()
        family_row = connection.sql(
            """
            select row_count, notes
            from warehouse_families
            where family_name = 'proteins'
            """
        ).fetchone()

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    proteins_family = next(
        item for item in manifest_payload["entity_families"] if item["family_name"] == "proteins"
    )

    assert placeholder_row == ("P69905-2", "protein:P69905-2", "P", "P6", "runtime-connectivity-2026-04-12")
    assert family_row is not None
    assert family_row[0] == 2
    assert "runtime_connectivity_placeholders_catalog_only" in (family_row[1] or [])
    assert proteins_family["row_count"] == 2
    assert "runtime_connectivity_placeholders_catalog_only" in proteins_family["notes"]


def test_materialize_library_asset_pack_copies_files_and_retargets_routes(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "warehouse"
    catalog_path = warehouse_root / "catalog" / "reference_library.duckdb"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = warehouse_root / "warehouse_manifest.json"
    source_registry_path = warehouse_root / "control" / "source_registry.json"
    receipt_path = warehouse_root / "control" / "asset_pack.latest.json"
    source_root = tmp_path / "archive" / "alphafold_db"
    source_root.mkdir(parents=True, exist_ok=True)
    (source_root / "swissprot_pdb_v6.tar").write_text("pdb-data", encoding="utf-8")
    (source_root / "swissprot_cif_v6.tar").write_text("cif-data", encoding="utf-8")

    manifest_path.write_text(
        json.dumps(
            {
                "warehouse_root": str(warehouse_root).replace("\\", "/"),
                "catalog_path": str(catalog_path).replace("\\", "/"),
                "entity_families": [
                    {
                        "family_name": "materialization_routes",
                        "partition_glob": str(
                            warehouse_root
                            / "partitions"
                            / "materialization_routes"
                            / "snapshot_id=test"
                            / "materialization_routes.parquet"
                        ).replace("\\", "/"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source_registry_path.parent.mkdir(parents=True, exist_ok=True)
    source_registry_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "source_id": "alphafold:current",
                        "source_family": "alphafold",
                        "snapshot_id": "current",
                        "integration_status": "promoted",
                        "authoritative_root": str(source_root).replace("\\", "/"),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with duckdb.connect(str(catalog_path)) as connection:
        connection.execute(
            """
            create table materialization_routes (
                route_id varchar,
                owner_summary_id varchar,
                owner_record_type varchar,
                materialization_kind varchar,
                pointer varchar,
                selector varchar,
                source_name varchar,
                source_record_id varchar,
                snapshot_id varchar,
                source_registry_anchor varchar,
                resolution_mode varchar,
                storage_contract varchar,
                external_dependency_cleared boolean
            )
            """
        )
        connection.execute(
            """
            insert into materialization_routes values
            (
                'route-1',
                'protein:P69905',
                'protein',
                'archive_member',
                ?,
                'AF-P69905-F1-model_v6.pdb.gz',
                'AlphaFold DB',
                'AFDB:P69905',
                'current',
                '',
                'library_archive_member',
                'library_owned_archive_member',
                true
            )
            """,
            [str(source_root / "swissprot_pdb_v6.tar").replace("\\", "/")],
        )

    payload = materialize_library_asset_pack(
        warehouse_manifest_path=manifest_path,
        source_registry_path=source_registry_path,
        output_receipt_path=receipt_path,
    )

    asset_pack_root = warehouse_root / "asset_packs" / "alphafold" / "current" / "alphafold_db"
    manifest_payload = json.loads((asset_pack_root / "_asset_pack_manifest.json").read_text(encoding="utf-8"))
    registry_payload = json.loads(source_registry_path.read_text(encoding="utf-8"))
    registry_row = registry_payload["records"][0]

    assert payload["status"] == "asset_pack_ready"
    assert payload["file_count"] == 2
    assert receipt_path.exists()
    assert (asset_pack_root / "swissprot_pdb_v6.tar").exists()
    assert (asset_pack_root / "swissprot_cif_v6.tar").exists()
    assert manifest_payload["storage_contract"] == "library_owned_asset_pack"
    assert registry_row["asset_pack_status"] == "ready"
    assert registry_row["asset_pack_root"] == str(asset_pack_root).replace("\\", "/")

    with duckdb.connect(str(catalog_path), read_only=True) as connection:
        route_row = connection.sql(
            """
            select pointer, source_registry_anchor, asset_pack_root, resolution_mode, storage_contract
            from materialization_routes
            """
        ).fetchone()

    assert route_row is not None
    assert route_row[0] == str(asset_pack_root / "swissprot_pdb_v6.tar").replace("\\", "/")
    assert route_row[1] == str(asset_pack_root).replace("\\", "/")
    assert route_row[2] == str(asset_pack_root).replace("\\", "/")
    assert route_row[3] == "library_asset_pack_member"
    assert route_row[4] == "library_owned_asset_pack_member"


def test_run_raw_disconnected_acceptance_passes_with_asset_pack_runtime(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "warehouse"
    catalog_path = warehouse_root / "catalog" / "reference_library.duckdb"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    (warehouse_root / "warehouse_manifest.json").write_text(
        json.dumps(
            {
                "warehouse_root": str(warehouse_root).replace("\\", "/"),
                "catalog_path": str(catalog_path).replace("\\", "/"),
                "catalog_engine": "duckdb",
                "catalog_status": "ready",
                "generated_at": "2026-04-13T00:00:00+00:00",
                "source_descriptors": [],
                "entity_families": [],
                "validation": {
                    "state": "passed",
                    "validated_at": "2026-04-13T00:00:00+00:00",
                    "checks": {},
                    "warnings": [],
                    "errors": [],
                },
                "export_policy": {},
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    source_registry_path = warehouse_root / "control" / "source_registry.json"
    source_registry_path.parent.mkdir(parents=True, exist_ok=True)
    asset_pack_root = warehouse_root / "asset_packs" / "alphafold" / "current" / "alphafold_db"
    asset_pack_root.mkdir(parents=True, exist_ok=True)
    (asset_pack_root / "swissprot_pdb_v6.tar").write_text("pdb-data", encoding="utf-8")
    source_registry_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "source_family": "alphafold",
                        "snapshot_id": "current",
                        "integration_status": "promoted",
                        "authoritative_root": str(tmp_path / "archive").replace("\\", "/"),
                        "asset_pack_root": str(asset_pack_root).replace("\\", "/"),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with duckdb.connect(str(catalog_path)) as connection:
        connection.execute(
            """
            create table materialization_routes (
                route_id varchar,
                pointer varchar,
                selector varchar,
                source_name varchar,
                snapshot_id varchar
            )
            """
        )
        connection.execute(
            """
            insert into materialization_routes values
            (
                'route-1',
                ?,
                'AF-P69905-F1-model_v6.pdb.gz',
                'AlphaFold DB',
                'current'
            )
            """,
            [str(asset_pack_root / "swissprot_pdb_v6.tar").replace("\\", "/")],
        )
        connection.execute(
            """
            create table proteins (
                accession varchar,
                protein_ref varchar,
                entry_name varchar,
                uniref100_cluster varchar,
                uniref90_cluster varchar,
                uniref50_cluster varchar,
                uniparc_id varchar,
                taxon_id bigint,
                accession_prefix1 varchar,
                accession_prefix2 varchar,
                snapshot_id varchar
            )
            """
        )
        connection.execute(
            """
            insert into proteins values
            ('P69905', 'protein:P69905', 'HBA_HUMAN', null, null, null, null, 9606, 'P', 'P6', 'seed')
            """
        )

    raw_root = tmp_path / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    receipt_path = warehouse_root / "control" / "offline_acceptance.latest.json"

    payload = run_raw_disconnected_acceptance(
        warehouse_root=warehouse_root,
        roots_to_mask=[raw_root],
        output_path=receipt_path,
        run_workspace_payload=False,
    )

    assert payload["status"] == "passed"
    assert receipt_path.exists()
    assert payload["library_checks"]["proteins_count"] == 1
    resolution = payload["library_checks"]["sample_materialization_resolution"]
    assert resolution["resolution_mode"] == "source_registry_anchor"
    assert resolution["asset_pack_root"] == str(asset_pack_root).replace("\\", "/")
    assert raw_root.exists()


def test_replace_runtime_path_preserves_incoming_mirror_references() -> None:
    source_root = Path(r"E:\ProteoSphere\reference_library")
    target_root = Path(r"D:\ProteoSphere\reference_library")
    payload = {
        "warehouse_root": "E:/ProteoSphere/reference_library",
        "catalog_path": "E:/ProteoSphere/reference_library/catalog/reference_library.duckdb",
        "mirror_root": "E:/ProteoSphere/reference_library/incoming_mirrors/string/current/string",
    }

    rewritten = _replace_runtime_path(payload, source_root, target_root)

    assert rewritten["warehouse_root"] == "D:/ProteoSphere/reference_library"
    assert rewritten["catalog_path"] == "D:/ProteoSphere/reference_library/catalog/reference_library.duckdb"
    assert rewritten["mirror_root"] == "E:/ProteoSphere/reference_library/incoming_mirrors/string/current/string"


def test_relocate_runtime_library_copies_runtime_surfaces_without_rewriting_mirror_paths(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root_posix = str(source_root).replace("\\", "/")
    target_root_posix = str(target_root).replace("\\", "/")
    for directory_name in ("catalog", "partitions", "normalized", "control", "exports", "incoming_mirrors"):
        (source_root / directory_name).mkdir(parents=True, exist_ok=True)
    (source_root / "catalog" / "reference_library.duckdb").write_text("duckdb", encoding="utf-8")
    (source_root / "warehouse_manifest.json").write_text(
        json.dumps(
            {
                "warehouse_root": source_root_posix,
                "catalog_path": f"{source_root_posix}/catalog/reference_library.duckdb",
                "entity_families": [
                    {
                        "family_name": "proteins",
                        "partition_glob": f"{source_root_posix}/partitions/proteins/snapshot_id=test/proteins.parquet",
                    }
                ],
                "mirror_root": f"{source_root_posix}/incoming_mirrors/string/current/string",
            }
        ),
        encoding="utf-8",
    )
    (source_root / "warehouse_summary.json").write_text(
        json.dumps(
            {
                "warehouse_root": source_root_posix,
                "catalog_path": f"{source_root_posix}/catalog/reference_library.duckdb",
                "warehouse_manifest_path": f"{source_root_posix}/warehouse_manifest.json",
            }
        ),
        encoding="utf-8",
    )

    payload = relocate_runtime_library(source_root=source_root, target_root=target_root)
    relocated_manifest = json.loads((target_root / "warehouse_manifest.json").read_text(encoding="utf-8"))

    assert payload["status"] == "relocated"
    assert (target_root / "catalog" / "reference_library.duckdb").exists()
    assert relocated_manifest["warehouse_root"] == target_root_posix
    assert relocated_manifest["catalog_path"].startswith(target_root_posix)
    assert relocated_manifest["mirror_root"] == f"{source_root_posix}/incoming_mirrors/string/current/string"


def test_execute_widened_scope_consolidation_copies_and_verifies_target(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "warehouse"
    source_root = tmp_path / "repo_raw" / "reactome" / "20260412T000000Z"
    source_root.mkdir(parents=True)
    (source_root / "pathways.tsv").write_text("R-HSA-1\tExample\n", encoding="utf-8")
    target_root = warehouse_root / "incoming_mirrors" / "reactome" / "20260412T000000Z" / "20260412T000000Z"
    plan_path = warehouse_root / "control" / "consolidation_plan.json"
    source_registry_path = warehouse_root / "control" / "source_registry.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(
            {
                "artifact_id": "widened_scope_consolidation_plan",
                "rows": [
                    {
                        "source_id": "reactome:20260412T000000Z",
                        "source_family": "reactome",
                        "snapshot_id": "20260412T000000Z",
                        "authoritative_root": str(source_root),
                        "source_roots": [str(source_root)],
                        "target_root": str(target_root),
                        "copy_required": True,
                        "consolidation_status": "pending",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source_registry_path.write_text(
        json.dumps(
            {
                "source_records": [
                    {
                        "source_id": "reactome:20260412T000000Z",
                        "source_family": "reactome",
                        "snapshot_id": "20260412T000000Z",
                        "authoritative_root": str(source_root),
                        "root_paths": [str(source_root)],
                        "consolidation_status": "pending",
                        "metadata": {"candidate_roots": [str(source_root)], "duplicate_roots": []},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    receipts_dir = warehouse_root / "control" / "consolidation_receipts"
    output_path = receipts_dir / "latest.json"

    payload = execute_widened_scope_consolidation(
        warehouse_root=warehouse_root,
        plan_path=plan_path,
        source_registry_path=source_registry_path,
        receipts_dir=receipts_dir,
        output_path=output_path,
        limit=None,
        source_family=None,
    )

    updated_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    updated_registry = json.loads(source_registry_path.read_text(encoding="utf-8"))
    assert payload["status"] == "executed"
    assert target_root.exists()
    assert updated_plan["rows"][0]["consolidation_status"] == "verified"
    assert updated_plan["rows"][0]["copy_required"] is False
    assert str(target_root) in updated_registry["source_records"][0]["root_paths"]
    assert output_path.exists()


def test_execute_widened_scope_consolidation_quarantines_mismatched_target(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "warehouse"
    source_root = tmp_path / "repo_raw" / "engineered_dataset"
    source_root.mkdir(parents=True)
    (source_root / "train.csv").write_text("id,label\n1,a\n", encoding="utf-8")
    target_root = warehouse_root / "incoming_mirrors" / "engineered_dataset" / "current" / "engineered_dataset"
    target_root.mkdir(parents=True)
    (target_root / "wrong.txt").write_text("wrong", encoding="utf-8")
    plan_path = warehouse_root / "control" / "consolidation_plan.json"
    source_registry_path = warehouse_root / "control" / "source_registry.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(
            {
                "artifact_id": "widened_scope_consolidation_plan",
                "rows": [
                    {
                        "source_id": "engineered_dataset:current",
                        "source_family": "engineered_dataset",
                        "snapshot_id": "current",
                        "authoritative_root": str(source_root),
                        "source_roots": [str(source_root)],
                        "target_root": str(target_root),
                        "copy_required": False,
                        "consolidation_status": "planned",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source_registry_path.write_text(
        json.dumps(
            {
                "source_records": [
                    {
                        "source_id": "engineered_dataset:current",
                        "source_family": "engineered_dataset",
                        "snapshot_id": "current",
                        "authoritative_root": str(source_root),
                        "root_paths": [str(source_root)],
                        "consolidation_status": "planned",
                        "metadata": {"candidate_roots": [str(source_root)], "duplicate_roots": []},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = execute_widened_scope_consolidation(
        warehouse_root=warehouse_root,
        plan_path=plan_path,
        source_registry_path=source_registry_path,
        receipts_dir=warehouse_root / "control" / "consolidation_receipts",
        output_path=warehouse_root / "control" / "consolidation_receipts" / "latest.json",
        limit=None,
        source_family=None,
    )

    receipt = payload["receipts"][0]
    quarantine_root = warehouse_root / "incoming_mirrors_quarantine" / "engineered_dataset__current"
    assert "quarantined_target" in receipt
    assert quarantine_root.exists()
    assert (target_root / "train.csv").exists()
    assert not (target_root / "wrong.txt").exists()


def test_execute_widened_scope_consolidation_ignores_blank_authoritative_root(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "warehouse"
    source_root = tmp_path / "repo_raw" / "engineered_dataset"
    source_root.mkdir(parents=True)
    (source_root / "train.csv").write_text("id,label\n1,a\n", encoding="utf-8")
    target_root = warehouse_root / "incoming_mirrors" / "engineered_dataset" / "current" / "engineered_dataset"
    plan_path = warehouse_root / "control" / "consolidation_plan.json"
    source_registry_path = warehouse_root / "control" / "source_registry.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(
            {
                "artifact_id": "widened_scope_consolidation_plan",
                "rows": [
                    {
                        "source_id": "engineered_dataset:current",
                        "source_family": "engineered_dataset",
                        "snapshot_id": "current",
                        "authoritative_root": "",
                        "source_roots": [str(source_root)],
                        "target_root": str(target_root),
                        "copy_required": True,
                        "consolidation_status": "planned",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source_registry_path.write_text(
        json.dumps(
            {
                "source_records": [
                    {
                        "source_id": "engineered_dataset:current",
                        "source_family": "engineered_dataset",
                        "snapshot_id": "current",
                        "authoritative_root": "",
                        "root_paths": [str(source_root)],
                        "consolidation_status": "planned",
                        "metadata": {"candidate_roots": [str(source_root)], "duplicate_roots": []},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = execute_widened_scope_consolidation(
        warehouse_root=warehouse_root,
        plan_path=plan_path,
        source_registry_path=source_registry_path,
        receipts_dir=warehouse_root / "control" / "consolidation_receipts",
        output_path=warehouse_root / "control" / "consolidation_receipts" / "latest.json",
        limit=None,
        source_family=None,
    )

    assert payload["receipts"][0]["source_root"] == str(source_root)
    assert (target_root / "train.csv").exists()


def test_execute_widened_scope_consolidation_resumes_partial_target_without_quarantine(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "warehouse"
    source_root = tmp_path / "repo_raw" / "string"
    source_root.mkdir(parents=True)
    (source_root / "a.txt").write_text("aaaa", encoding="utf-8")
    (source_root / "b.txt").write_text("bbbb", encoding="utf-8")
    target_root = warehouse_root / "incoming_mirrors" / "string" / "current" / "string"
    target_root.mkdir(parents=True, exist_ok=True)
    (target_root / "a.txt").write_text("aaaa", encoding="utf-8")
    plan_path = warehouse_root / "control" / "consolidation_plan.json"
    source_registry_path = warehouse_root / "control" / "source_registry.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(
            {
                "artifact_id": "widened_scope_consolidation_plan",
                "rows": [
                    {
                        "source_id": "string:current",
                        "source_family": "string",
                        "snapshot_id": "current",
                        "authoritative_root": str(source_root),
                        "source_roots": [str(source_root)],
                        "target_root": str(target_root),
                        "copy_required": True,
                        "consolidation_status": "pending",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source_registry_path.write_text(
        json.dumps(
            {
                "source_records": [
                    {
                        "source_id": "string:current",
                        "source_family": "string",
                        "snapshot_id": "current",
                        "authoritative_root": str(source_root),
                        "root_paths": [str(source_root)],
                        "consolidation_status": "pending",
                        "metadata": {"candidate_roots": [str(source_root)], "duplicate_roots": []},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = execute_widened_scope_consolidation(
        warehouse_root=warehouse_root,
        plan_path=plan_path,
        source_registry_path=source_registry_path,
        receipts_dir=warehouse_root / "control" / "consolidation_receipts",
        output_path=warehouse_root / "control" / "consolidation_receipts" / "latest.json",
        limit=None,
        source_family=None,
    )

    receipt = payload["receipts"][0]
    assert receipt["status"] == "verified"
    assert receipt["resume_in_place"] is True
    assert "quarantined_target" not in receipt
    assert (target_root / "b.txt").exists()


def test_plan_widened_scope_consolidation_treats_verified_warehouse_root_as_satisfied(tmp_path: Path) -> None:
    warehouse_root = tmp_path / "warehouse"
    warehouse_root.mkdir(parents=True)
    source_registry_path = warehouse_root / "control" / "source_registry.json"
    output_path = warehouse_root / "control" / "consolidation_plan.json"
    source_registry_path.parent.mkdir(parents=True, exist_ok=True)

    source_root = tmp_path / "repo_raw" / "catalog"
    source_root.mkdir(parents=True)
    (source_root / "catalog.json").write_text("{}", encoding="utf-8")
    warehouse_catalog = warehouse_root / "catalog"
    warehouse_catalog.mkdir(parents=True)
    (warehouse_catalog / "catalog.json").write_text("{}", encoding="utf-8")

    source_registry_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "source_id": "catalog:current",
                        "source_family": "catalog",
                        "snapshot_id": "current",
                        "authoritative_root": str(source_root),
                        "root_paths": [str(source_root), str(warehouse_catalog)],
                        "consolidation_status": "verified",
                        "consolidation_target": str(
                            warehouse_root / "incoming_mirrors" / "catalog" / "current" / "catalog"
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = plan_widened_scope_consolidation(
        warehouse_root=warehouse_root,
        source_registry_path=source_registry_path,
        output_path=output_path,
    )

    assert payload["rows"][0]["copy_required"] is False
    assert payload["summary"]["copy_required_count"] == 0


def test_import_existing_scraped_data_materializes_normalized_claims(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    (status_dir / "targeted_page_scrape_registry_preview.json").write_text(
        json.dumps(
            {
                "artifact_id": "targeted_page_scrape_registry_preview",
                "status": "report_only",
                "rows": [
                    {"accession": "P04637", "source_url": "https://example.org/p53"},
                    {"accession": "P31749", "source_url": "https://example.org/akt1"},
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = tmp_path / "warehouse" / "normalized" / "scrape_enrichment" / "existing_scraped_data" / "current"

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    claims_path = normalized_root / "scraped_claim_rows.jsonl"
    manifest_path = normalized_root / "manifest.json"
    assert payload["summary"]["claim_row_count"] == 2
    assert claims_path.exists()
    assert manifest_path.exists()
    first_row = json.loads(claims_path.read_text(encoding="utf-8").splitlines()[0])
    assert first_row["scraped_claims"][0]["accession"] == "P04637"
    assert first_row["best_evidence_claims"] == []


def test_import_existing_scraped_data_preserves_structure_targets(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    (status_dir / "pdb_enrichment_harvest_preview.json").write_text(
        json.dumps(
            {
                "artifact_id": "pdb_enrichment_harvest_preview",
                "status": "report_only_live_harvest",
                "rows": [
                    {
                        "structure_id": "4HHB",
                        "successful_source_count": 3,
                        "expected_source_count": 3,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    assert payload["summary"]["artifact_count"] == 1
    assert payload["summary"]["claim_row_count"] == 1
    claim = payload["claim_rows"][0]
    assert claim["accession"] is None
    assert claim["structure_id"] == "4HHB"
    assert claim["linked_authoritative_target"] == "4HHB"

    claims_path = normalized_root / "scraped_claim_rows.jsonl"
    first_row = json.loads(claims_path.read_text(encoding="utf-8").splitlines()[0])
    assert first_row["structure_id"] == "4HHB"
    assert first_row["linked_authoritative_target"] == "4HHB"


def test_import_existing_scraped_data_preserves_ligand_targets(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    (status_dir / "structure_ligand_context_preview.json").write_text(
        json.dumps(
            {
                "artifact_id": "structure_ligand_context_preview",
                "status": "report_only_live_harvest",
                "rows": [
                    {
                        "structure_id": "1Y01",
                        "ccd_id": "HEM",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    claim = payload["claim_rows"][0]
    assert claim["structure_id"] == "1Y01"
    assert claim["ligand_id"] == "HEM"
    assert claim["linked_authoritative_target"] == "1Y01"

    claims_path = normalized_root / "scraped_claim_rows.jsonl"
    first_row = json.loads(claims_path.read_text(encoding="utf-8").splitlines()[0])
    assert first_row["ligand_id"] == "HEM"


def test_import_existing_scraped_data_supports_entry_payloads(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    (status_dir / "local_bridge_ligand_payloads.real.json").write_text(
        json.dumps(
            {
                "task_id": "local_bridge_ligand_payloads",
                "entries": [
                    {
                        "accession": "Q9NZD4",
                        "pdb_id": "1Y01",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    assert payload["summary"]["artifact_count"] == 1
    assert payload["summary"]["claim_row_count"] == 1
    artifact = payload["artifacts"][0]
    assert artifact["artifact_id"] == "local_bridge_ligand_payloads.real"
    assert artifact["row_count"] == 1


def test_import_existing_scraped_data_preserves_measurement_targets(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    (status_dir / "binding_measurement_registry_preview.json").write_text(
        json.dumps(
            {
                "artifact_id": "binding_measurement_registry_preview",
                "status": "complete",
                "rows": [
                    {
                        "pdb_id": "2TPI",
                        "measurement_id": "binding_measurement:pdbbind:PL:2TPI:Kd",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    claim = payload["claim_rows"][0]
    assert claim["pdb_id"] == "2TPI"
    assert claim["measurement_id"] == "binding_measurement:pdbbind:PL:2TPI:Kd"
    assert claim["linked_authoritative_target"] == "2TPI"

    claims_path = normalized_root / "scraped_claim_rows.jsonl"
    first_row = json.loads(claims_path.read_text(encoding="utf-8").splitlines()[0])
    assert first_row["pdb_id"] == "2TPI"
    assert first_row["measurement_id"] == "binding_measurement:pdbbind:PL:2TPI:Kd"


def test_import_existing_scraped_data_counts_binding_support_artifacts(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    (status_dir / "bindingdb_target_polymer_context_preview.json").write_text(
        json.dumps(
            {
                "artifact_id": "bindingdb_target_polymer_context_preview",
                "status": "report_only_local_harvest",
                "rows": [
                    {
                        "accession": "P04637",
                        "bindingdb_polymer_presence": "present",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (status_dir / "bindingdb_structure_bridge_preview.json").write_text(
        json.dumps(
            {
                "artifact_id": "bindingdb_structure_bridge_preview",
                "status": "report_only_local_harvest",
                "rows": [
                    {
                        "structure_id": "4HHB",
                        "bindingdb_bridge_status": "present",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    assert payload["summary"]["artifact_count"] == 2
    assert payload["summary"]["claim_row_count"] == 2
    artifact_ids = {artifact["artifact_id"] for artifact in payload["artifacts"]}
    assert artifact_ids == {
        "bindingdb_target_polymer_context_preview",
        "bindingdb_structure_bridge_preview",
    }


def test_import_existing_scraped_data_preserves_bindingdb_source_native_ids(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    (status_dir / "bindingdb_measurement_subset_preview.json").write_text(
        json.dumps(
            {
                "artifact_id": "bindingdb_measurement_subset_preview",
                "status": "report_only_local_harvest",
                "rows": [
                    {
                        "measurement_id": "binding_measurement:bindingdb:15809:IC50:P31749",
                        "accession": "P31749",
                        "source_record_id": "15809",
                        "bindingdb_polymer_id": "513",
                        "primary_structure_or_target_ref": "protein:P31749",
                        "measurement_origin": "bindingdb",
                        "source_name": "BindingDB local dump",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    claim = payload["claim_rows"][0]
    assert claim["source_record_id"] == "15809"
    assert claim["bindingdb_polymer_id"] == "513"
    assert claim["primary_structure_or_target_ref"] == "protein:P31749"
    assert claim["measurement_origin"] == "bindingdb"
    assert claim["source_name"] == "BindingDB local dump"

    claims_path = normalized_root / "scraped_claim_rows.jsonl"
    first_row = json.loads(claims_path.read_text(encoding="utf-8").splitlines()[0])
    assert first_row["source_record_id"] == "15809"
    assert first_row["bindingdb_polymer_id"] == "513"


def test_import_existing_scraped_data_preserves_bindingdb_monomer_ids(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    (status_dir / "bindingdb_partner_monomer_context_preview.json").write_text(
        json.dumps(
            {
                "artifact_id": "bindingdb_partner_monomer_context_preview",
                "status": "report_only_local_projection",
                "rows": [
                    {
                        "bindingdb_monomer_id": "102307",
                        "source_name": "BindingDB partner monomer projection",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    claim = payload["claim_rows"][0]
    assert claim["bindingdb_monomer_id"] == "102307"
    assert claim["source_name"] == "BindingDB partner monomer projection"


def test_import_existing_scraped_data_counts_extended_bindingdb_profiles(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    artifact_payloads = {
        "bindingdb_accession_assay_profile_preview.json": {
            "artifact_id": "bindingdb_accession_assay_profile_preview",
            "status": "report_only_local_projection",
            "rows": [{"accession": "P04637"}],
        },
        "bindingdb_accession_partner_identity_profile_preview.json": {
            "artifact_id": "bindingdb_accession_partner_identity_profile_preview",
            "status": "report_only_local_projection",
            "rows": [{"accession": "P04637"}],
        },
        "bindingdb_assay_condition_profile_preview.json": {
            "artifact_id": "bindingdb_assay_condition_profile_preview",
            "status": "report_only_local_projection",
            "rows": [{"accession": "P04637"}],
        },
        "bindingdb_structure_assay_summary_preview.json": {
            "artifact_id": "bindingdb_structure_assay_summary_preview",
            "status": "report_only_local_projection",
            "rows": [{"structure_id": "4HHB"}],
        },
        "binding_measurement_suspect_rows_preview.json": {
            "artifact_id": "binding_measurement_suspect_rows_preview",
            "status": "report_only",
            "rows": [{"measurement_id": "binding_measurement:chembl_lightweight:P00387:CHEMBL101021:93255"}],
        },
    }
    for name, payload in artifact_payloads.items():
        (status_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    assert payload["summary"]["artifact_count"] == 5
    assert payload["summary"]["claim_row_count"] == 5
    artifact_ids = {artifact["artifact_id"] for artifact in payload["artifacts"]}
    assert artifact_ids == {
        "bindingdb_accession_assay_profile_preview",
        "bindingdb_accession_partner_identity_profile_preview",
        "bindingdb_assay_condition_profile_preview",
        "bindingdb_structure_assay_summary_preview",
        "binding_measurement_suspect_rows_preview",
    }


def test_import_existing_scraped_data_preserves_full_source_row(tmp_path: Path) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    source_row = {
        "structure_id": "10GS",
        "complex_type": "protein_ligand",
        "affinity_measurement_count": 1,
        "measurements": [
            {
                "measurement_id": "binding_measurement:pdbbind:PL:10GS:Ki",
                "measurement_type": "Ki",
            }
        ],
    }
    (status_dir / "structure_binding_affinity_context_preview.json").write_text(
        json.dumps(
            {
                "artifact_id": "structure_binding_affinity_context_preview",
                "status": "complete",
                "rows": [source_row],
            }
        ),
        encoding="utf-8",
    )
    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    claim = payload["claim_rows"][0]
    assert claim["structure_id"] == "10GS"
    assert claim["source_row"]["complex_type"] == "protein_ligand"
    assert claim["source_row"]["measurements"][0]["measurement_id"] == "binding_measurement:pdbbind:PL:10GS:Ki"

    claims_path = normalized_root / "scraped_claim_rows.jsonl"
    first_row = json.loads(claims_path.read_text(encoding="utf-8").splitlines()[0])
    assert first_row["scraped_claims"][0]["source_row"]["affinity_measurement_count"] == 1


def test_import_existing_scraped_data_counts_protein_interaction_structure_context_artifacts(
    tmp_path: Path,
) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    artifact_payloads = {
        "protein_function_context_preview.json": {
            "artifact_id": "protein_function_context_preview",
            "status": "report_only_live_harvest",
            "rows": [{"accession": "P04637", "source_url": "https://rest.uniprot.org/uniprotkb/P04637.json"}],
        },
        "protein_reference_context_preview.json": {
            "artifact_id": "protein_reference_context_preview",
            "status": "report_only_live_harvest",
            "rows": [{"accession": "P04637", "reference_count": 237}],
        },
        "interaction_partner_context_preview.json": {
            "artifact_id": "interaction_partner_context_preview",
            "status": "complete",
            "rows": [{"accession": "P04637", "partner_count": 4}],
        },
        "structure_binding_affinity_context_preview.json": {
            "artifact_id": "structure_binding_affinity_context_preview",
            "status": "complete",
            "rows": [{"structure_id": "10GS", "affinity_measurement_count": 1}],
        },
        "structure_publication_context_preview.json": {
            "artifact_id": "structure_publication_context_preview",
            "status": "report_only_live_harvest",
            "rows": [{"structure_id": "4HHB", "citation_pubmed_id": 6726807}],
        },
    }
    for name, payload in artifact_payloads.items():
        (status_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    assert payload["summary"]["artifact_count"] == 5
    assert payload["summary"]["claim_row_count"] == 5
    artifact_ids = {artifact["artifact_id"] for artifact in payload["artifacts"]}
    assert artifact_ids == {
        "protein_function_context_preview",
        "protein_reference_context_preview",
        "interaction_partner_context_preview",
        "structure_binding_affinity_context_preview",
        "structure_publication_context_preview",
    }


def test_import_existing_scraped_data_counts_origin_and_validation_context_artifacts(
    tmp_path: Path,
) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    artifact_payloads = {
        "protein_feature_context_preview.json": {
            "artifact_id": "protein_feature_context_preview",
            "status": "report_only_live_harvest",
            "rows": [{"accession": "P04637", "feature_count": 1518}],
        },
        "protein_origin_context_preview.json": {
            "artifact_id": "protein_origin_context_preview",
            "status": "report_only_live_harvest",
            "rows": [{"accession": "P04637", "reviewed": True}],
        },
        "interaction_origin_context_preview.json": {
            "artifact_id": "interaction_origin_context_preview",
            "status": "complete",
            "rows": [{"accession": "P04637", "physical_evidence_count": 3}],
        },
        "structure_origin_context_preview.json": {
            "artifact_id": "structure_origin_context_preview",
            "status": "report_only_live_harvest",
            "rows": [{"structure_id": "4HHB", "chain_count": 4}],
        },
        "structure_validation_context_preview.json": {
            "artifact_id": "structure_validation_context_preview",
            "status": "report_only_live_harvest",
            "rows": [{"structure_id": "4HHB", "experimental_method": "X-RAY DIFFRACTION"}],
        },
    }
    for name, payload in artifact_payloads.items():
        (status_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    assert payload["summary"]["artifact_count"] == 5
    assert payload["summary"]["claim_row_count"] == 5
    artifact_ids = {artifact["artifact_id"] for artifact in payload["artifacts"]}
    assert artifact_ids == {
        "protein_feature_context_preview",
        "protein_origin_context_preview",
        "interaction_origin_context_preview",
        "structure_origin_context_preview",
        "structure_validation_context_preview",
    }


def test_import_existing_scraped_data_counts_enzyme_and_structure_context_artifacts(
    tmp_path: Path,
) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    artifact_payloads = {
        "enzyme_behavior_context_preview.json": {
            "artifact_id": "enzyme_behavior_context_preview",
            "status": "complete",
            "rows": [{"accession": "P00387", "kinetics_support_status": "supported_now"}],
        },
        "catalytic_site_context_preview.json": {
            "artifact_id": "catalytic_site_context_preview",
            "status": "report_only",
            "rows": [{"accession": "P00387", "protein_name": "NADH-cytochrome b5 reductase 3"}],
        },
        "kinetics_enzyme_support_preview.json": {
            "artifact_id": "kinetics_enzyme_support_preview",
            "status": "complete",
            "rows": [{"accession": "P00387", "protein_ref": "protein:P00387"}],
        },
        "structure_assembly_context_preview.json": {
            "artifact_id": "structure_assembly_context_preview",
            "status": "report_only_live_harvest",
            "rows": [{"structure_id": "4HHB", "assembly_count": 1}],
        },
        "structure_chain_origin_preview.json": {
            "artifact_id": "structure_chain_origin_preview",
            "status": "report_only_live_harvest",
            "rows": [{"structure_id": "4HHB", "chain_id": "A"}],
        },
    }
    for name, payload in artifact_payloads.items():
        (status_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    assert payload["summary"]["artifact_count"] == 5
    assert payload["summary"]["claim_row_count"] == 5
    artifact_ids = {artifact["artifact_id"] for artifact in payload["artifacts"]}
    assert artifact_ids == {
        "enzyme_behavior_context_preview",
        "catalytic_site_context_preview",
        "kinetics_enzyme_support_preview",
        "structure_assembly_context_preview",
        "structure_chain_origin_preview",
    }


def test_import_existing_scraped_data_counts_cluster_similarity_and_affinity_artifacts(
    tmp_path: Path,
) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    artifact_payloads = {
        "uniref_cluster_context_preview.json": {
            "artifact_id": "uniref_cluster_context_preview",
            "status": "report_only_live_harvest",
            "rows": [{"accession": "P00387", "uniref100_cluster_id": "UniRef100_P00387"}],
        },
        "interaction_similarity_signature_preview.json": {
            "artifact_id": "interaction_similarity_signature_preview",
            "status": "complete",
            "rows": [{"accession": "P69905", "signature_id": "interaction_similarity:P69905"}],
        },
        "structure_affinity_best_evidence_preview.json": {
            "artifact_id": "structure_affinity_best_evidence_preview",
            "status": "report_only",
            "rows": [{"structure_id": "10GS", "selected_evidence_kind": "exact"}],
        },
        "structure_similarity_signature_preview.json": {
            "artifact_id": "structure_similarity_signature_preview",
            "status": "complete",
            "rows": [{"accession": "P68871", "entity_ref": "structure_unit:protein:P68871:4HHB:B"}],
        },
    }
    for name, payload in artifact_payloads.items():
        (status_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    assert payload["summary"]["artifact_count"] == 4
    assert payload["summary"]["claim_row_count"] == 4
    artifact_ids = {artifact["artifact_id"] for artifact in payload["artifacts"]}
    assert artifact_ids == {
        "uniref_cluster_context_preview",
        "interaction_similarity_signature_preview",
        "structure_affinity_best_evidence_preview",
        "structure_similarity_signature_preview",
    }


def test_import_existing_scraped_data_counts_protein_ligand_variant_bridge_artifacts(
    tmp_path: Path,
) -> None:
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    artifact_payloads = {
        "protein_similarity_signature_preview.json": {
            "artifact_id": "protein_similarity_signature_preview",
            "status": "complete",
            "rows": [{"accession": "P00387", "signature_id": "protein_similarity:protein:P00387"}],
        },
        "ligand_identity_core_materialization_preview.json": {
            "artifact_id": "ligand_identity_core_materialization_preview",
            "status": "complete",
            "rows": [{"accession": "P00387", "source_ref": "ligand:P00387"}],
        },
        "ligand_row_materialization_preview.json": {
            "artifact_id": "ligand_row_materialization_preview",
            "status": "complete",
            "rows": [{"accession": "P00387", "row_id": "ligand_row:protein:P00387:chembl:CHEMBL35888"}],
        },
        "ligand_similarity_signature_preview.json": {
            "artifact_id": "ligand_similarity_signature_preview",
            "status": "complete",
            "rows": [{"accession": "P00387", "signature_id": "ligand_similarity:ligand_row:protein:P00387:chembl:CHEMBL35888"}],
        },
        "structure_variant_bridge_summary.json": {
            "artifact_id": "structure_variant_bridge_summary",
            "status": "complete",
            "rows": [{"protein_ref": "protein:P68871", "variant_count": 263}],
            "overlap_rows": [{"protein_ref": "protein:P68871", "variant_count": 263}],
        },
    }
    for name, payload in artifact_payloads.items():
        (status_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    output_path = status_dir / "existing_scraped_data_registry.json"
    normalized_root = (
        tmp_path
        / "warehouse"
        / "normalized"
        / "scrape_enrichment"
        / "existing_scraped_data"
        / "current"
    )

    payload = import_existing_scraped_data(
        status_dir=status_dir,
        output_path=output_path,
        normalized_root=normalized_root,
    )

    assert payload["summary"]["artifact_count"] == 5
    assert payload["summary"]["claim_row_count"] == 5
    artifact_ids = {artifact["artifact_id"] for artifact in payload["artifacts"]}
    assert artifact_ids == {
        "protein_similarity_signature_preview",
        "ligand_identity_core_materialization_preview",
        "ligand_row_materialization_preview",
        "ligand_similarity_signature_preview",
        "structure_variant_bridge_summary",
    }


def test_run_targeted_page_scrape_capture_normalizes_html_pages(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_fetch(url: str) -> tuple[bytes, str]:
        if "uniprot" in url:
            return (
                json.dumps(
                    {
                        "proteinDescription": {
                            "recommendedName": {"fullName": {"value": "Example protein"}}
                        },
                        "genes": [{"geneName": {"value": "EXAMPLE"}}],
                        "features": [{"type": "DOMAIN"}],
                        "keywords": [{"id": "KW-1"}],
                    }
                ).encode("utf-8"),
                "application/json",
            )
        if "interpro" in url:
            return (
                b"<html><head><title>InterPro Example</title><meta name=\"description\" content=\"InterPro description\"></head></html>",
                "text/html; charset=UTF-8",
            )
        return (
            b"<html><head><title>Reactome Example</title><meta name=\"description\" content=\"Reactome description\"></head></html>",
            "text/html; charset=UTF-8",
        )

    monkeypatch.setattr("scripts.run_targeted_page_scrape_capture._fetch", fake_fetch)

    raw_registry, normalization_preview, support_preview = run_targeted_page_scrape_capture(
        {
            "rows": [
                {
                    "accession": "P12345",
                    "candidate_pages": [
                        "https://rest.uniprot.org/uniprotkb/P12345.json",
                        "https://www.ebi.ac.uk/interpro/protein/UniProt/P12345/",
                        "https://reactome.org/content/query?q=P12345",
                    ],
                }
            ]
        },
        raw_root=tmp_path / "page_scrape" / "raw",
    )

    assert raw_registry["summary"]["payload_count"] == 3
    assert normalization_preview["summary"]["normalized_row_count"] == 3
    assert {row["source_kind"] for row in normalization_preview["rows"]} == {
        "uniprot_rest_json",
        "interpro_html_page",
        "reactome_query_page",
    }
    html_rows = [row for row in normalization_preview["rows"] if row["source_kind"] != "uniprot_rest_json"]
    assert all(row["page_title"] for row in html_rows)
    assert support_preview["summary"]["accession_count"] == 1


def test_run_targeted_page_scrape_capture_merges_with_existing_wave_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_fetch(url: str) -> tuple[bytes, str]:
        accession = url.rsplit("/", 1)[-1].split(".", 1)[0].split("?", 1)[0]
        return (
            json.dumps(
                {
                    "proteinDescription": {
                        "recommendedName": {"fullName": {"value": f"Protein {accession}"}}
                    },
                    "genes": [{"geneName": {"value": accession}}],
                    "features": [{"type": "DOMAIN"}],
                    "keywords": [{"id": "KW-1"}],
                }
            ).encode("utf-8"),
            "application/json",
        )

    monkeypatch.setattr("scripts.run_targeted_page_scrape_capture._fetch", fake_fetch)

    raw_registry, normalization_preview, support_preview = run_targeted_page_scrape_capture(
        {
            "rows": [
                {
                    "accession": "P12345",
                    "candidate_pages": ["https://rest.uniprot.org/uniprotkb/P12345.json"],
                }
            ]
        },
        raw_root=tmp_path / "page_scrape" / "raw",
        existing_raw_registry={
            "rows": [
                {
                    "accession": "P00001",
                    "source_url": "https://rest.uniprot.org/uniprotkb/P00001.json",
                    "payload_path": "existing-a",
                }
            ]
        },
        existing_normalization_preview={
            "rows": [
                {
                    "accession": "P00001",
                    "source_kind": "uniprot_rest_json",
                    "source_url": "https://rest.uniprot.org/uniprotkb/P00001.json",
                    "protein_name": "Protein P00001",
                }
            ]
        },
        existing_support_preview={
            "rows": [
                {
                    "accession": "P00001",
                    "candidate_page_count": 1,
                    "payload_refs": ["existing-a"],
                    "normalized_fact_refs": ["uniprot_rest_json"],
                }
            ]
        },
    )

    assert raw_registry["summary"]["payload_count"] == 2
    assert normalization_preview["summary"]["normalized_row_count"] == 2
    assert support_preview["summary"]["accession_count"] == 2
    assert [row["accession"] for row in support_preview["rows"]] == ["P00001", "P12345"]
