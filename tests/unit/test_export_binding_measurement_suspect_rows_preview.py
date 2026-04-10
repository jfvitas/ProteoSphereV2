from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_export(tmp_path: Path) -> tuple[dict[str, object], str]:
    output_json = tmp_path / "binding_measurement_suspect_rows_preview.json"
    output_md = tmp_path / "binding_measurement_suspect_rows_preview.md"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_binding_measurement_suspect_rows_preview.py"),
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
    return json.loads(output_json.read_text(encoding="utf-8")), output_md.read_text(
        encoding="utf-8"
    )


def test_export_binding_measurement_suspect_rows_preview(tmp_path: Path) -> None:
    payload, markdown = _run_export(tmp_path)

    assert payload["status"] == "report_only"
    assert payload["row_count"] == 5171
    assert payload["summary"]["suspect_accession_count"] == 6
    assert payload["summary"]["measurement_origin_counts"] == {
        "bindingdb": 5150,
        "chembl_lightweight": 21,
    }
    assert payload["summary"]["accession_support_status_counts"] == {
        "grounded preview-safe": 20,
        "support-only": 5151,
    }
    assert payload["summary"]["suspect_reason_counts"]["candidate_only"] == 5151
    assert (
        payload["summary"]["suspect_reason_counts"]["confidence:bindingdb_exact_value_without_unit"]
        == 4245
    )
    assert payload["summary"]["suspect_reason_counts"]["confidence:unparsed"] == 906
    assert payload["summary"]["suspect_reason_counts"]["missing_measurement_type"] == 1
    assert "Binding Measurement Suspect Rows Preview" in markdown

    rows = {row["measurement_id"]: row for row in payload["rows"]}
    assert (
        rows["binding_measurement:chembl_lightweight:P00387:CHEMBL66165:56842"][
            "accession_support_status"
        ]
        == "grounded preview-safe"
    )
    assert rows["binding_measurement:chembl_lightweight:P00387:CHEMBL66165:56842"][
        "suspect_reason_codes"
    ] == ["confidence:exact_relation_non_comparable"]
    assert any(
        row["accession"] == "P31749" and row["measurement_origin"] == "bindingdb"
        for row in payload["rows"]
    )
    assert (
        sum(
            1
            for row in payload["rows"]
            if row["accession"] == "P31749" and row["measurement_origin"] == "bindingdb"
        )
        == 5072
    )
    assert any(
        row["accession"] == "Q9NZD4"
        and row["measurement_origin"] == "chembl_lightweight"
        and row["accession_support_status"] == "support-only"
        and "candidate_only" in row["suspect_reason_codes"]
        for row in payload["rows"]
    )
