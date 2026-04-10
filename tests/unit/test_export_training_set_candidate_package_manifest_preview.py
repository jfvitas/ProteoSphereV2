from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_training_set_candidate_package_manifest_preview import (
    build_training_set_candidate_package_manifest_preview,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_training_set_candidate_package_manifest_preview_merges_preview_surfaces() -> None:
    training_set_readiness = {
        "summary": {
            "selected_count": 3,
            "package_ready": False,
            "blocked_reasons": ["fold_export_ready=false"],
        },
        "readiness_rows": [
            {
                "accession": "P00387",
                "training_set_state": "governing_ready",
                "packet_status": "partial",
                "recommended_next_step": "keep_visible_for_preview_compilation",
            },
            {
                "accession": "Q9NZD4",
                "training_set_state": "preview_visible_non_governing",
                "packet_status": "partial",
                "recommended_next_step": "keep_non_governing_until_real_ligand_rows_exist",
            },
            {
                "accession": "P09105",
                "training_set_state": "blocked_pending_acquisition",
                "packet_status": "partial",
                "recommended_next_step": "wait_for_source_fix:ligand:P00387",
            },
        ],
    }
    cohort_compiler = {
        "row_count": 3,
        "rows": [
            {
                "accession": "P00387",
                "split": "train",
                "bucket": "moderate_coverage",
                "ligand_readiness_ladder": "grounded preview-safe",
                "source_lanes": ["UniProt"],
            },
            {
                "accession": "Q9NZD4",
                "split": "train",
                "bucket": "moderate_coverage",
                "ligand_readiness_ladder": "candidate-only non-governing",
                "source_lanes": ["UniProt"],
            },
            {
                "accession": "P09105",
                "split": "test",
                "bucket": "sparse_or_control",
                "ligand_readiness_ladder": "support-only",
                "source_lanes": ["UniProt"],
            },
        ],
    }
    package_readiness = {
        "summary": {
            "ready_for_package": False,
            "blocked_reasons": ["fold_export_ready=false", "cv_fold_export_unlocked=false"],
        }
    }

    payload = build_training_set_candidate_package_manifest_preview(
        training_set_readiness,
        cohort_compiler,
        package_readiness,
    )

    assert payload["status"] == "report_only"
    assert payload["manifest_status"] == "candidate_package_blocked_pending_readiness"
    assert payload["summary"]["selected_count"] == 3
    assert payload["summary"]["governing_preview_row_count"] == 1
    assert payload["summary"]["candidate_only_non_governing_count"] == 1
    assert payload["summary"]["support_only_non_governing_count"] == 0
    assert payload["summary"]["blocked_pending_acquisition_count"] == 1
    assert payload["rows"][1]["package_role"] == "candidate_only_non_governing"
    assert payload["rows"][2]["package_role"] == "blocked_pending_acquisition"
    assert payload["truth_boundary"]["package_not_authorized"] is True
    assert payload["truth_boundary"]["non_mutating"] is True


def test_export_training_set_candidate_package_manifest_preview_writes_outputs(
    tmp_path: Path,
) -> None:
    training_set_readiness_path = tmp_path / "training_set_readiness_preview.json"
    cohort_compiler_path = tmp_path / "cohort_compiler_preview.json"
    package_readiness_path = tmp_path / "package_readiness_preview.json"
    output_json = tmp_path / "training_set_candidate_package_manifest_preview.json"
    output_md = tmp_path / "training_set_candidate_package_manifest_preview.md"

    training_set_readiness_path.write_text(
        json.dumps(
            {
                "summary": {"selected_count": 1, "package_ready": False, "blocked_reasons": []},
                "readiness_rows": [
                    {
                        "accession": "P00387",
                        "training_set_state": "governing_ready",
                        "packet_status": "partial",
                        "recommended_next_step": "keep_visible_for_preview_compilation",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    cohort_compiler_path.write_text(
        json.dumps(
            {
                "row_count": 1,
                "rows": [
                    {
                        "accession": "P00387",
                        "split": "train",
                        "bucket": "moderate_coverage",
                        "ligand_readiness_ladder": "grounded preview-safe",
                        "source_lanes": ["UniProt"],
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    package_readiness_path.write_text(
        json.dumps({"summary": {"ready_for_package": False, "blocked_reasons": []}}, indent=2),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(
                REPO_ROOT / "scripts" / "export_training_set_candidate_package_manifest_preview.py"
            ),
            "--training-set-readiness",
            str(training_set_readiness_path),
            "--cohort-compiler",
            str(cohort_compiler_path),
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
    assert payload["artifact_id"] == "training_set_candidate_package_manifest_preview"
    assert payload["summary"]["selected_count"] == 1
    assert payload["rows"][0]["package_role"] == "governing_preview_row"
    assert "Training Set Candidate Package Manifest Preview" in output_md.read_text(
        encoding="utf-8"
    )
