from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_ligand_stage1_validation_panel_preview(tmp_path: Path) -> None:
    p00387_validation = tmp_path / "p00387.json"
    q9nzd4_validation = tmp_path / "q9nzd4.json"
    output_json = tmp_path / "panel.json"
    output_md = tmp_path / "panel.md"

    p00387_validation.write_text(
        json.dumps(
            {
                "status": "aligned",
                "accession": "P00387",
                "target_chembl_id": "CHEMBL2146",
                "truth_boundary": {"ready_for_operator_preview": True},
            }
        ),
        encoding="utf-8",
    )
    q9nzd4_validation.write_text(
        json.dumps(
            {
                "status": "aligned",
                "accession": "Q9NZD4",
                "best_pdb_id": "1Y01",
                "truth_boundary": {"ready_for_operator_preview": True},
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(
                REPO_ROOT
                / "scripts"
                / "export_ligand_stage1_validation_panel_preview.py"
            ),
            "--p00387-validation",
            str(p00387_validation),
            "--q9nzd4-validation",
            str(q9nzd4_validation),
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

    artifact = json.loads(output_json.read_text(encoding="utf-8"))
    assert artifact["status"] == "complete"
    assert artifact["row_count"] == 2
    assert artifact["summary"]["validated_accessions"] == ["P00387", "Q9NZD4"]
    assert artifact["summary"]["aligned_row_count"] == 2
    assert artifact["summary"]["candidate_only_accessions"] == ["Q9NZD4"]
    assert artifact["truth_boundary"]["ligand_rows_materialized"] is False
    assert "Ligand Stage1 Validation Panel Preview" in output_md.read_text(
        encoding="utf-8"
    )
