from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_sabio_rk_support_preview(tmp_path: Path) -> None:
    output_json = tmp_path / "sabio_rk_support_preview.json"
    output_md = tmp_path / "sabio_rk_support_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_sabio_rk_support_preview.py"),
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
    assert payload["artifact_id"] == "sabio_rk_support_preview"
    assert payload["status"] == "complete"
    assert payload["row_count"] == 11
    assert payload["summary"]["matrix_accession_count"] == 11
    assert payload["summary"]["sabio_seed_accession_count"] == 6943
    assert payload["summary"]["supported_accession_count"] == 3
    assert payload["summary"]["unsupported_accession_count"] == 8
    assert payload["summary"]["supported_accessions"] == [
        "P00387",
        "P04637",
        "P31749",
    ]
    assert payload["summary"]["supported_high_priority_accession_count"] == 2
    assert payload["summary"]["supported_observe_accession_count"] == 1
    assert payload["summary"]["query_scope_field_present"] is True
    assert payload["summary"]["dashboard_status"] == "blocked_on_release_grade_bar"
    assert payload["summary"]["operator_go_no_go"] == "no-go"
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["live_kinetic_ids_verified"] is False
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P00387"]["sabio_support_status"] == "supported_now"
    assert rows["P04637"]["sabio_support_status"] == "supported_now"
    assert rows["P31749"]["sabio_support_status"] == "supported_now"
    assert rows["Q9NZD4"]["sabio_support_status"] == "no_local_sabio_seed_coverage"
    assert "SABIO-RK Support Preview" in output_md.read_text(encoding="utf-8")
