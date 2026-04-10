from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_leakage_group_preview(tmp_path: Path) -> None:
    leakage_signature_preview = {
        "rows": [
            {
                "accession": "P1",
                "protein_ref": "protein:P1",
                "exact_accession_group": "P1",
                "sequence_checksum_group": "seq-1",
                "structure_signature_group": None,
                "domain_signature_group": "dom-1",
                "pathway_signature_group": None,
                "motif_signature_group": "mot-1",
                "variant_count": 3,
                "structure_ids": [],
                "candidate_status": None,
                "leakage_risk_class": "structure_followup",
                "truth_note": "variant-bearing accession without structure slice",
            },
            {
                "accession": "P2",
                "protein_ref": "protein:P2",
                "exact_accession_group": "P2",
                "sequence_checksum_group": "seq-2",
                "structure_signature_group": "struct-2",
                "domain_signature_group": "dom-2",
                "pathway_signature_group": None,
                "motif_signature_group": "mot-2",
                "variant_count": 4,
                "structure_ids": ["1ABC"],
                "candidate_status": "candidate_only_no_variant_anchor",
                "leakage_risk_class": "candidate_overlap",
                "truth_note": "candidate overlap",
            },
        ]
    }
    assignment_preview = {
        "group_rows": [
            {
                "linked_group_id": "protein:P1",
                "split_name": "train",
                "entity_count": 4,
                "entity_family_counts": {"protein": 1, "protein_variant": 3},
            },
            {
                "linked_group_id": "protein:P2",
                "split_name": "test",
                "entity_count": 5,
                "entity_family_counts": {
                    "protein": 1,
                    "protein_variant": 3,
                    "structure_unit": 1,
                },
            },
        ]
    }
    leakage_path = tmp_path / "leakage_signature_preview.json"
    assignment_path = tmp_path / "entity_split_assignment_preview.json"
    output_json = tmp_path / "leakage_group_preview.json"
    output_md = tmp_path / "leakage_group_preview.md"
    leakage_path.write_text(json.dumps(leakage_signature_preview), encoding="utf-8")
    assignment_path.write_text(json.dumps(assignment_preview), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_leakage_group_preview.py"),
            "--leakage-signature-preview",
            str(leakage_path),
            "--entity-split-assignment-preview",
            str(assignment_path),
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
    assert payload["row_count"] == 2
    assert payload["summary"]["split_group_counts"] == {"train": 1, "test": 1}
    assert payload["summary"]["risk_class_counts"] == {
        "structure_followup": 1,
        "candidate_overlap": 1,
    }
    assert payload["truth_boundary"]["ready_for_bundle_preview"] is True
    assert "Leakage Group Preview" in output_md.read_text(encoding="utf-8")
