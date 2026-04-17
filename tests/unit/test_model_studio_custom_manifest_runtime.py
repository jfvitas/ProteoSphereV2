from __future__ import annotations

import json

import duckdb
import pytest

from api.model_studio import runtime
from api.model_studio.contracts import SplitPlanSpec, TrainingSetRequestSpec
from api.model_studio.paper_evaluator.pipeline import (
    evaluate_explicit_manifest,
    load_live_warehouse_snapshot,
)


def _seed_accessions() -> list[str]:
    catalog_path = runtime._custom_dataset_warehouse_catalog_path()
    if not catalog_path.exists():
        pytest.skip(f"warehouse catalog not available: {catalog_path}")
    with duckdb.connect(str(catalog_path), read_only=True) as con:
        rows = con.execute(
            """
            SELECT accession
            FROM proteins
            WHERE accession IS NOT NULL AND accession <> ''
            LIMIT 4
            """
        ).fetchall()
    accessions = [str(row[0]) for row in rows if row and row[0]]
    if len(accessions) < 4:
        pytest.skip("need at least four accessions from the warehouse for the custom-manifest runtime test")
    return accessions


def test_runtime_custom_manifest_round_trip_and_preview(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(runtime, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(runtime, "CUSTOM_DATASET_DIR", tmp_path / "runtime" / "custom_datasets")

    accession_a, accession_b, accession_c, accession_d = _seed_accessions()
    payload = {
        "manifest_id": "manifest:test-runtime-overlap",
        "title": "Runtime overlap manifest",
        "task_type": "protein-protein",
        "label_type": "delta_G",
        "entity_kind": "protein_pair",
        "split_membership_mode": "explicit_manifest",
        "records": [
            {
                "record_id": "train-1",
                "split": "train",
                "protein_a": accession_a,
                "protein_b": accession_b,
                "label_value": -10.1,
                "provenance_note": "runtime test train",
            },
            {
                "record_id": "val-1",
                "split": "val",
                "protein_a": accession_c,
                "protein_b": accession_d,
                "label_value": -9.4,
                "provenance_note": "runtime test val",
            },
            {
                "record_id": "test-1",
                "split": "test",
                "protein_a": accession_a,
                "protein_b": accession_d,
                "label_value": -8.7,
                "provenance_note": "runtime test overlap",
            },
        ],
    }

    validation = runtime.validate_custom_dataset_manifest(payload)
    assert validation["status"] == "ready"
    assert validation["split_counts"] == {"train": 1, "val": 1, "test": 1}
    assert validation["resolved_rows"] == 3
    assert validation["unresolved_rows"] == 0
    assert validation["grounding_coverage"] == 1.0

    assessment = evaluate_explicit_manifest(payload, load_live_warehouse_snapshot())
    assert assessment["evaluation_mode"] == "explicit_manifest"
    assert assessment["verdict"] == "unsafe_for_training"
    assert "DIRECT_OVERLAP" in assessment["reason_codes"]
    assert assessment["needs_human_review"] is False

    imported = runtime.import_custom_dataset_manifest(payload)
    assert imported["dataset_ref"] == "custom_study:manifest:test-runtime-overlap"
    assert imported["storage_key"] == "manifest_test-runtime-overlap"

    loaded_manifest = runtime.load_custom_dataset_manifest("manifest:test-runtime-overlap")
    assert loaded_manifest["dataset_ref"] == "custom_study:manifest:test-runtime-overlap"
    assert loaded_manifest["validation"]["grounding_coverage"] == 1.0

    listed = runtime.list_custom_dataset_manifests()
    assert listed[0]["dataset_ref"] == "custom_study:manifest:test-runtime-overlap"

    preview = runtime.preview_training_set_request(
        TrainingSetRequestSpec(
            request_id="req:custom-runtime-preview",
            task_type="protein-protein",
            label_type="delta_G",
            structure_source_policy="experimental_only",
            dataset_refs=("custom_study:manifest:test-runtime-overlap",),
            target_size=3,
        ),
        SplitPlanSpec(
            plan_id="split:custom-runtime-preview",
            objective="explicit_manifest",
            grouping_policy="explicit_manifest",
            holdout_policy="explicit_membership",
        ),
    )
    assert preview["custom_split_mode"] is True
    assert preview["resolved_dataset_refs"] == ["custom_study:manifest:test-runtime-overlap"]
    assert preview["candidate_preview"]["final_selected_count"] == 3
    assert preview["split_preview"]["membership_locked"] is True
    assert preview["split_preview"]["train_count"] == 1
    assert preview["split_preview"]["val_count"] == 1
    assert preview["split_preview"]["test_count"] == 1
    assert {row["split"] for row in preview["candidate_preview"]["rows"]} == {"train", "val", "test"}

    manifest_dir = runtime.CUSTOM_DATASET_DIR / "manifest_test-runtime-overlap"
    persisted = json.loads((manifest_dir / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert persisted["dataset_ref"] == "custom_study:manifest:test-runtime-overlap"
    assert persisted["validation"]["grounding_coverage"] == 1.0


def test_custom_dataset_validation_prefers_env_warehouse_root(tmp_path, monkeypatch) -> None:
    warehouse_root = tmp_path / "warehouse"
    catalog_dir = warehouse_root / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = catalog_dir / "reference_library.duckdb"
    with duckdb.connect(str(catalog_path)) as con:
        con.execute(
            """
            CREATE TABLE proteins (
                accession VARCHAR,
                protein_ref VARCHAR,
                entry_name VARCHAR,
                uniref100_cluster VARCHAR,
                uniref90_cluster VARCHAR,
                uniref50_cluster VARCHAR,
                uniparc_id VARCHAR,
                taxon_id BIGINT,
                accession_prefix1 VARCHAR,
                accession_prefix2 VARCHAR,
                snapshot_id VARCHAR
            )
            """
        )
        con.execute(
            """
            INSERT INTO proteins VALUES
            ('P12345', 'pref-1', 'ENTRY_A', 'UniRef100_P12345', 'UniRef90_P12345', 'UniRef50_P12345', NULL, 9606, 'P', 'P1', 'snap-1'),
            ('Q67890', 'pref-2', 'ENTRY_B', 'UniRef100_Q67890', 'UniRef90_Q67890', 'UniRef50_Q67890', NULL, 9606, 'Q', 'Q6', 'snap-1')
            """
        )

    monkeypatch.setenv("PROTEOSPHERE_WAREHOUSE_ROOT", str(warehouse_root))

    payload = {
        "manifest_id": "manifest:test-env-priority",
        "title": "Env priority manifest",
        "task_type": "protein-protein",
        "label_type": "delta_G",
        "entity_kind": "protein_pair",
        "split_membership_mode": "explicit_manifest",
        "records": [
            {
                "record_id": "train-1",
                "split": "train",
                "protein_a": "P12345",
                "protein_b": "Q67890",
                "label_value": -8.0,
                "provenance_note": "env train",
            },
            {
                "record_id": "val-1",
                "split": "val",
                "protein_a": "Q67890",
                "protein_b": "P12345",
                "label_value": -7.5,
                "provenance_note": "env val",
            },
            {
                "record_id": "test-1",
                "split": "test",
                "protein_a": "P12345",
                "protein_b": "Q67890",
                "label_value": -7.2,
                "provenance_note": "env test",
            },
        ],
    }

    validation = runtime.validate_custom_dataset_manifest(payload)
    assert validation["warehouse_resolution"]["catalog_path"] == str(catalog_path)
    assert validation["resolved_rows"] == 3
    assert validation["unresolved_rows"] == 0


def test_explicit_manifest_preview_ignores_source_family_and_fallback_expansion(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(runtime, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(runtime, "CUSTOM_DATASET_DIR", tmp_path / "runtime" / "custom_datasets")

    accession_a, accession_b, accession_c, accession_d = _seed_accessions()
    payload = {
        "manifest_id": "manifest:test-explicit-exclusive",
        "title": "Explicit manifest exclusive",
        "task_type": "protein-protein",
        "label_type": "delta_G",
        "entity_kind": "protein_pair",
        "split_membership_mode": "explicit_manifest",
        "records": [
            {
                "record_id": "train-1",
                "split": "train",
                "protein_a": accession_a,
                "protein_b": accession_b,
                "label_value": -10.0,
            },
            {
                "record_id": "val-1",
                "split": "val",
                "protein_a": accession_c,
                "protein_b": accession_d,
                "label_value": -9.0,
            },
            {
                "record_id": "test-1",
                "split": "test",
                "protein_a": accession_a,
                "protein_b": accession_d,
                "label_value": -8.0,
            },
        ],
    }

    runtime.import_custom_dataset_manifest(payload)

    preview = runtime.preview_training_set_request(
        TrainingSetRequestSpec(
            request_id="req:explicit-exclusive",
            task_type="protein-protein",
            label_type="delta_G",
            structure_source_policy="experimental_only",
            dataset_refs=("custom_study:manifest:test-explicit-exclusive",),
            source_families=("PDBbind v2020",),
            target_size=3,
        ),
        SplitPlanSpec(
            plan_id="split:explicit-exclusive",
            objective="explicit_manifest",
            grouping_policy="explicit_manifest",
            holdout_policy="explicit_membership",
        ),
        fallback_dataset_refs=("release_pp_alpha_benchmark_v1",),
    )

    assert preview["custom_split_mode"] is True
    assert preview["resolved_dataset_refs"] == ["custom_study:manifest:test-explicit-exclusive"]
    assert preview["candidate_preview"]["final_selected_count"] == 3
