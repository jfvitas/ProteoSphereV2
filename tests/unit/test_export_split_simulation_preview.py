from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_split_simulation_preview(tmp_path: Path) -> None:
    split_labels = {
        "manifest_id": "benchmark-cohort-manifest-2026-03-22",
        "split_policy": "accession-level only",
        "counts": {
            "total": 12,
            "train": 8,
            "val": 2,
            "test": 2,
            "resolved": 12,
            "unresolved": 0,
        },
        "labels": [
            {
                "accession": "P69905",
                "split": "train",
                "bucket": "rich_coverage",
                "leakage_key": "P69905",
                "status": "resolved",
            },
            {
                "accession": "P68871",
                "split": "train",
                "bucket": "rich_coverage",
                "leakage_key": "P68871",
                "status": "resolved",
            },
            {
                "accession": "P04637",
                "split": "train",
                "bucket": "rich_coverage",
                "leakage_key": "P04637",
                "status": "resolved",
            },
            {
                "accession": "P31749",
                "split": "train",
                "bucket": "rich_coverage",
                "leakage_key": "P31749",
                "status": "resolved",
            },
            {
                "accession": "Q9NZD4",
                "split": "train",
                "bucket": "moderate_coverage",
                "leakage_key": "Q9NZD4",
                "status": "resolved",
            },
            {
                "accession": "Q2TAC2",
                "split": "train",
                "bucket": "moderate_coverage",
                "leakage_key": "Q2TAC2",
                "status": "resolved",
            },
            {
                "accession": "P00387",
                "split": "train",
                "bucket": "moderate_coverage",
                "leakage_key": "P00387",
                "status": "resolved",
            },
            {
                "accession": "P02042",
                "split": "train",
                "bucket": "moderate_coverage",
                "leakage_key": "P02042",
                "status": "resolved",
            },
            {
                "accession": "P02100",
                "split": "val",
                "bucket": "sparse_or_control",
                "leakage_key": "P02100",
                "status": "resolved",
            },
            {
                "accession": "P69892",
                "split": "val",
                "bucket": "sparse_or_control",
                "leakage_key": "P69892",
                "status": "resolved",
            },
            {
                "accession": "P09105",
                "split": "test",
                "bucket": "sparse_or_control",
                "leakage_key": "P09105",
                "status": "resolved",
            },
            {
                "accession": "Q9UCM0",
                "split": "test",
                "bucket": "sparse_or_control",
                "leakage_key": "Q9UCM0",
                "status": "resolved",
            },
        ],
        "leakage_ready": {
            "accession_level_only": True,
            "duplicate_accessions": [],
            "cross_split_duplicates": [],
        },
    }
    dry_run_validation = {
        "status": "aligned",
        "validation": {
            "issues": [],
            "matches": [
                "recipe_input_artifact",
                "candidate_row_count",
                "assignment_count",
                "assignment_vs_simulation_count",
            ],
            "candidate_row_count": 1889,
            "assignment_count": 1889,
            "split_group_counts": {"test": 9, "train": 1, "val": 1},
            "row_level_split_counts": {"test": 183, "train": 1440, "val": 266},
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 1440},
                {"linked_group_id": "protein:P68871", "split_name": "val", "entity_count": 266},
                {"linked_group_id": "protein:P69905", "split_name": "test", "entity_count": 152},
                {"linked_group_id": "protein:P31749", "split_name": "test", "entity_count": 24},
            ],
        },
    }
    fold_gate = {
        "status": "blocked_pending_unlock",
        "gate": {
            "gate_id": "cv_fold_export_unlock_gate",
            "gate_surface": "split_engine_input_preview",
            "required_condition_count": 4,
            "blocked_today_reason": "gate remains closed",
        },
        "validation_snapshot": {
            "dry_run_validation_status": "aligned",
            "candidate_row_count": 1889,
            "assignment_count": 1889,
        },
        "unlock_readiness": {
            "cv_fold_export_unlocked": False,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_folds_materialized=false",
                "final_split_committed=false",
            ],
        },
    }
    post_staging = {
        "status": "blocked_report_emitted",
        "gate_check": {
            "gate_status": "blocked_pending_unlock",
        },
        "blocked_report": {
            "blocked": True,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_folds_materialized=false",
                "final_split_committed=false",
            ],
        },
        "staging_parity": {
            "candidate_row_count": 1889,
            "assignment_count": 1889,
        },
    }
    package_readiness = {
        "artifact_id": "package_readiness_preview",
        "status": "report_only",
        "summary": {
            "packet_count": 12,
            "ready_for_package": False,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            ],
        },
    }

    split_labels_path = tmp_path / "split_labels.json"
    dry_run_path = tmp_path / "split_engine_dry_run_validation.json"
    fold_gate_path = tmp_path / "split_fold_export_gate_preview.json"
    post_staging_path = tmp_path / "split_post_staging_gate_check_preview.json"
    package_readiness_path = tmp_path / "package_readiness_preview.json"
    output_json = tmp_path / "split_simulation_preview.json"
    output_md = tmp_path / "split_simulation_preview.md"
    split_labels_path.write_text(json.dumps(split_labels), encoding="utf-8")
    dry_run_path.write_text(json.dumps(dry_run_validation), encoding="utf-8")
    fold_gate_path.write_text(json.dumps(fold_gate), encoding="utf-8")
    post_staging_path.write_text(json.dumps(post_staging), encoding="utf-8")
    package_readiness_path.write_text(json.dumps(package_readiness), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_split_simulation_preview.py"),
            "--split-labels",
            str(split_labels_path),
            "--split-engine-dry-run-validation",
            str(dry_run_path),
            "--split-fold-export-gate",
            str(fold_gate_path),
            "--split-post-staging-gate-check",
            str(post_staging_path),
            "--package-readiness",
            str(package_readiness_path),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "report_only"
    assert payload["summary"]["label_count"] == 12
    assert payload["summary"]["split_counts"] == {"test": 2, "train": 8, "val": 2}
    assert payload["summary"]["dry_run_validation_status"] == "aligned"
    assert payload["summary"]["dry_run_issue_count"] == 0
    assert payload["summary"]["fold_export_gate_status"] == "blocked_pending_unlock"
    assert payload["summary"]["cv_fold_export_unlocked"] is False
    assert payload["summary"]["post_staging_gate_status"] == "blocked_report_emitted"
    assert payload["summary"]["package_ready"] is False
    assert "fold_export_ready=false" in payload["summary"]["package_blocking_factors"]
    assert payload["rows"][0]["accession"] == "P69905"
    assert "Split Simulation Preview" in output_md.read_text(encoding="utf-8")
