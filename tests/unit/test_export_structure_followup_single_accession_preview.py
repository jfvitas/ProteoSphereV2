from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_structure_followup_single_accession_preview(tmp_path: Path) -> None:
    promotion_plan = {
        "promotion_plan": {
            "selected_accession": "P31749",
            "deferred_accession": "P04637",
        },
        "promotion_gate": {"must_preserve": ["coverage"]},
        "operator_effect": {"single_accession_scope": True},
    }
    payload_preview = {
        "payload_rows": [
            {
                "accession": "P31749",
                "variant_ref": "protein_variant:protein:P31749:K14Q",
                "structure_id": "7NH5",
                "chain_id": "A",
                "coverage": 0.927,
            },
            {
                "accession": "P04637",
                "variant_ref": "protein_variant:protein:P04637:Q5H",
                "structure_id": "9R2Q",
                "chain_id": "K",
                "coverage": 1.0,
            },
        ]
    }

    plan_path = tmp_path / "plan.json"
    preview_path = tmp_path / "preview.json"
    output_json = tmp_path / "single.json"
    output_md = tmp_path / "single.md"
    plan_path.write_text(json.dumps(promotion_plan), encoding="utf-8")
    preview_path.write_text(json.dumps(payload_preview), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_structure_followup_single_accession_preview.py"),
            "--promotion-plan",
            str(plan_path),
            "--payload-preview",
            str(preview_path),
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
    assert payload["status"] == "complete"
    assert payload["selected_accession"] == "P31749"
    assert payload["deferred_accession"] == "P04637"
    assert payload["payload_row"]["structure_id"] == "7NH5"
    assert payload["truth_boundary"]["single_accession_scope"] is True
    assert "Structure Follow-Up Single Accession Preview" in output_md.read_text(
        encoding="utf-8"
    )
