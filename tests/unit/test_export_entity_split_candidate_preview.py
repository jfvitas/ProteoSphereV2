from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_entity_split_candidate_preview(tmp_path: Path) -> None:
    preview = {
        "rows": [
            {
                "entity_ref": "protein:P1",
                "entity_family": "protein",
                "accession": "P1",
                "protein_ref": "protein:P1",
                "exact_entity_group": "protein:P1",
                "protein_spine_group": "protein:P1",
                "sequence_equivalence_group": "seq:p1",
                "variant_delta_group": None,
                "structure_chain_group": None,
                "structure_fold_group": None,
                "ligand_identity_group": None,
                "binding_context_group": None,
                "family_readiness": {
                    "protein": True,
                    "protein_variant": False,
                    "structure_unit": False,
                    "protein_ligand": False,
                },
            },
            {
                "entity_ref": "protein_variant:protein:P1:A10V",
                "entity_family": "protein_variant",
                "accession": "P1",
                "protein_ref": "protein:P1",
                "exact_entity_group": "protein_variant:protein:P1:A10V",
                "protein_spine_group": "protein:P1",
                "sequence_equivalence_group": "protein:P1",
                "variant_delta_group": "A10V",
                "structure_chain_group": None,
                "structure_fold_group": None,
                "ligand_identity_group": None,
                "binding_context_group": None,
                "family_readiness": {
                    "protein": True,
                    "protein_variant": True,
                    "structure_unit": False,
                    "protein_ligand": False,
                },
            },
            {
                "entity_ref": "structure_unit:protein:P1:1ABC:A",
                "entity_family": "structure_unit",
                "accession": "P1",
                "protein_ref": "protein:P1",
                "exact_entity_group": "structure_unit:protein:P1:1ABC:A",
                "protein_spine_group": "protein:P1",
                "sequence_equivalence_group": "protein:P1",
                "variant_delta_group": None,
                "structure_chain_group": "1ABC:A",
                "structure_fold_group": "fold:1",
                "ligand_identity_group": None,
                "binding_context_group": None,
                "family_readiness": {
                    "protein": True,
                    "protein_variant": False,
                    "structure_unit": True,
                    "protein_ligand": False,
                },
            },
        ]
    }
    preview_path = tmp_path / "entity_signature_preview.json"
    preview_path.write_text(json.dumps(preview), encoding="utf-8")
    output_json = tmp_path / "entity_split_candidate_preview.json"
    output_md = tmp_path / "entity_split_candidate_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_entity_split_candidate_preview.py"),
            "--entity-signature-preview",
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
    assert payload["row_count"] == 3
    assert payload["summary"]["linked_group_count"] == 1
    assert payload["summary"]["entity_family_counts"] == {
        "protein": 1,
        "protein_variant": 1,
        "structure_unit": 1,
    }
    structure_row = next(
        row for row in payload["candidate_rows"] if row["entity_family"] == "structure_unit"
    )
    assert structure_row["bucket"] == "structure_entity"
    assert structure_row["validation_class"] == "structure_candidate_overlap"
    assert structure_row["lane_depth"] == 3
    assert payload["truth_boundary"]["ready_for_split_engine"] is True
    assert "Entity Split Candidate Preview" in output_md.read_text(encoding="utf-8")
