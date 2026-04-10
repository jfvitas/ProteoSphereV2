from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_p00387_ligand_extraction_validation_preview(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.json"
    payload_path = tmp_path / "payload.json"
    output_json = tmp_path / "preview.json"
    output_md = tmp_path / "preview.md"

    contract_path.write_text(
        json.dumps(
            {
                "contract_status": "ready_for_next_step",
                "live_signal": {
                    "selected_target_hit": {
                        "chembl_id": "CHEMBL2146",
                        "pref_name": "NADH-cytochrome b5 reductase",
                        "activity_count": 93,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    payload_path.write_text(
        json.dumps(
            {
                "status": "resolved",
                "summary": {
                    "target_chembl_id": "CHEMBL2146",
                    "target_pref_name": "NADH-cytochrome b5 reductase",
                    "activity_count_total": 93,
                    "rows_emitted": 25,
                    "distinct_assay_count_in_payload": 10,
                    "distinct_ligand_count_in_payload": 23,
                    "top_ligand_chembl_id": "CHEMBL35888",
                },
                "rows": [
                    {
                        "ligand_chembl_id": "CHEMBL35888",
                        "standard_type": "IC50",
                        "standard_value": 10840,
                        "standard_units": "nM",
                    }
                ],
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
                / "export_p00387_ligand_extraction_validation_preview.py"
            ),
            "--contract",
            str(contract_path),
            "--payload",
            str(payload_path),
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
    assert artifact["status"] == "aligned"
    assert artifact["accession"] == "P00387"
    assert artifact["target_chembl_id"] == "CHEMBL2146"
    assert artifact["activity_count_total"] == 93
    assert artifact["rows_emitted"] == 25
    assert artifact["validation_summary"]["ready_for_operator_preview"] is True
    assert artifact["truth_boundary"]["canonical_ligand_materialization_claimed"] is False
    assert "P00387 Ligand Extraction Validation Preview" in output_md.read_text(
        encoding="utf-8"
    )
