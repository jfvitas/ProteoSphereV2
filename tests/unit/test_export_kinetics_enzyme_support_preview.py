from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_kinetics_enzyme_support_preview(tmp_path: Path) -> None:
    output_json = tmp_path / "kinetics_enzyme_support_preview.json"
    output_md = tmp_path / "kinetics_enzyme_support_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_kinetics_enzyme_support_preview.py"),
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
    assert payload["artifact_id"] == "kinetics_enzyme_support_preview"
    assert payload["policy_family"] == "kinetics_support_compact_family"
    assert payload["policy_label"] == "preview_bundle_safe_non_governing"
    assert payload["row_count"] == 11
    assert payload["summary"]["supported_accession_count"] == 3
    assert payload["summary"]["unsupported_accession_count"] == 8
    assert payload["summary"]["sabio_supported_accession_count"] == 3
    assert payload["summary"]["enzyme_supported_accession_count"] == 3
    assert payload["summary"]["dual_supported_accession_count"] == 3
    assert payload["summary"]["single_source_supported_accession_count"] == 0
    assert payload["summary"]["supported_accessions"] == [
        "P00387",
        "P04637",
        "P31749",
    ]
    assert payload["summary"]["dashboard_status"] == "blocked_on_release_grade_bar"
    assert payload["summary"]["operator_go_no_go"] == "no-go"
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["ready_for_bundle_preview"] is True
    assert payload["truth_boundary"]["governing_for_split_or_leakage"] is False
    assert payload["truth_boundary"]["live_kinetic_ids_verified"] is False
    assert payload["truth_boundary"]["live_enzyme_activity_verified"] is False
    assert output_md.exists()

    supported_rows = [
        row for row in payload["rows"] if row["kinetics_support_status"] == "supported_now"
    ]
    assert [row["accession"] for row in supported_rows] == [
        "P00387",
        "P04637",
        "P31749",
    ]
    assert supported_rows[0]["support_sources"] == ["sabio_rk", "pdb_chain_enzyme"]
    assert supported_rows[1]["support_sources"] == ["sabio_rk", "pdb_chain_enzyme"]
    assert supported_rows[2]["support_sources"] == ["sabio_rk", "pdb_chain_enzyme"]

    q9_row = next(row for row in payload["rows"] if row["accession"] == "Q9NZD4")
    assert q9_row["kinetics_support_status"] == "no_local_accession_resolved_support"
