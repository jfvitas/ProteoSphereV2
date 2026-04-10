from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_entity_split_simulation_preview(tmp_path: Path) -> None:
    preview = {
        "candidate_rows": [
            {
                "canonical_id": "protein:P1",
                "entity_family": "protein",
                "accession": "P1",
                "protein_ref": "protein:P1",
                "leakage_key": "protein:P1",
                "linked_group_id": "protein:P1",
                "bucket": "protein_spine",
                "validation_class": "protein_backbone",
                "lane_depth": 1,
            },
            {
                "canonical_id": "protein_variant:protein:P1:A10V",
                "entity_family": "protein_variant",
                "accession": "P1",
                "protein_ref": "protein:P1",
                "leakage_key": "protein_variant:protein:P1:A10V",
                "linked_group_id": "protein:P1",
                "bucket": "variant_entity",
                "validation_class": "variant_entity",
                "lane_depth": 2,
            },
            {
                "canonical_id": "protein:P2",
                "entity_family": "protein",
                "accession": "P2",
                "protein_ref": "protein:P2",
                "leakage_key": "protein:P2",
                "linked_group_id": "protein:P2",
                "bucket": "protein_spine",
                "validation_class": "protein_backbone",
                "lane_depth": 1,
            },
        ]
    }
    input_path = tmp_path / "entity_split_candidate_preview.json"
    output_json = tmp_path / "entity_split_simulation_preview.json"
    output_md = tmp_path / "entity_split_simulation_preview.md"
    input_path.write_text(json.dumps(preview), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_entity_split_simulation_preview.py"),
            "--entity-split-candidates",
            str(input_path),
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
    assert payload["summary"]["candidate_row_count"] == 3
    assert payload["summary"]["assignment_count"] == 3
    assert payload["summary"]["rejected_count"] == 0
    assert payload["recipe"]["recipe_id"] == "recipe:entity-split-preview:v1"
    assert payload["summary"]["family_counts_by_split"]
    assert payload["truth_boundary"]["final_split_committed"] is False
    assert "Entity Split Simulation Preview" in output_md.read_text(encoding="utf-8")
