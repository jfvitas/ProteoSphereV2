from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_export(tmp_path: Path) -> dict[str, object]:
    output_json = tmp_path / "structure_affinity_best_evidence_preview.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_structure_affinity_best_evidence_preview.py"),
            "--output-json",
            str(output_json),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(output_json.read_text(encoding="utf-8"))


def test_export_structure_affinity_best_evidence_preview(tmp_path: Path) -> None:
    payload = _run_export(tmp_path)

    assert payload["status"] == "report_only"
    assert payload["row_count"] == 23010
    assert payload["summary"]["exact_structure_count"] == 22638
    assert payload["summary"]["derived_structure_count"] == 372
    assert payload["summary"]["support_only_structure_count"] == 0
    assert payload["summary"]["selected_evidence_kind_counts"] == {
        "exact": 22638,
        "derived": 372,
        "support_only": 0,
    }
    assert payload["summary"]["structure_surface_support_count"] == 2
    assert payload["summary"]["structure_surface_ligand_count"] == 2
    assert payload["summary"]["support_accession_count"] == 2
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["exact_over_derived"] is True

    rows = {row["structure_id"]: row for row in payload["rows"]}
    assert rows["10GS"]["selected_evidence_kind"] == "exact"
    assert rows["10GS"]["best_exact_affinity"]["measurement_type"] == "Ki"
    assert rows["10GS"]["selected_evidence"]["evidence_kind"] == "exact"
    assert any(row["selected_evidence_kind"] == "derived" for row in payload["rows"])

    support_rows = {
        row["structure_id"]: row for row in payload["supporting_structure_surfaces"]["entry_rows"]
    }
    assert support_rows["1Y01"]["accession_support_rows"][0]["accession"] == "Q9NZD4"
    assert (
        support_rows["1Y01"]["accession_support_rows"][0]["support_status"]
        == "candidate_only_non_governing"
    )
    assert support_rows["4HHB"]["accession_support_rows"][0]["accession"] == "P68871"
    assert support_rows["4HHB"]["accession_support_rows"][0]["measurement_count"] == 9
