from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_kinetics_enzyme_support_preview(tmp_path: Path) -> None:
    preview_json = tmp_path / "kinetics_enzyme_support_preview.json"
    preview_md = tmp_path / "kinetics_enzyme_support_preview.md"
    validation_json = tmp_path / "kinetics_enzyme_support_validation.json"
    validation_md = tmp_path / "kinetics_enzyme_support_validation.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_kinetics_enzyme_support_preview.py"),
            "--output-json",
            str(preview_json),
            "--output-md",
            str(preview_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_kinetics_enzyme_support_preview.py"),
            "--kinetics-support-preview",
            str(preview_json),
            "--output-json",
            str(validation_json),
            "--output-md",
            str(validation_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(validation_json.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == "kinetics_enzyme_support_validation"
    assert payload["status"] == "aligned"
    assert payload["validation"]["issue_count"] == 0
    assert payload["validation"]["warning_count"] == 1
    assert payload["validation"]["row_count"] == 11
    assert payload["validation"]["supported_accession_count"] == 3
    assert payload["validation"]["unsupported_accession_count"] == 8
    assert payload["validation"]["sabio_supported_accession_count"] == 3
    assert payload["validation"]["enzyme_supported_accession_count"] == 3
    assert payload["validation"]["dual_supported_accession_count"] == 3
    assert payload["validation"]["single_source_supported_accession_count"] == 0
    assert payload["validation"]["supported_accessions"] == [
        "P00387",
        "P04637",
        "P31749",
    ]
    assert payload["validation"]["unsupported_accessions"] == [
        "P02042",
        "P02100",
        "P09105",
        "P68871",
        "P69892",
        "P69905",
        "Q2TAC2",
        "Q9NZD4",
    ]
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["local_source_only"] is True
    assert payload["truth_boundary"]["live_kinetic_ids_verified"] is False
    assert payload["truth_boundary"]["live_enzyme_activity_verified"] is False
    assert validation_md.exists()
