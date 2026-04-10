from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_entity_split_assignment_preview(tmp_path: Path) -> None:
    candidates = {
        "candidate_rows": [
            {
                "canonical_id": "protein:P1",
                "entity_family": "protein",
                "accession": "P1",
                "protein_ref": "protein:P1",
                "leakage_key": "protein:P1",
                "linked_group_id": "protein:P1",
                "lane_depth": 1,
            },
            {
                "canonical_id": "protein_variant:protein:P1:A10V",
                "entity_family": "protein_variant",
                "accession": "P1",
                "protein_ref": "protein:P1",
                "leakage_key": "protein_variant:protein:P1:A10V",
                "linked_group_id": "protein:P1",
                "lane_depth": 2,
            },
            {
                "canonical_id": "protein:P2",
                "entity_family": "protein",
                "accession": "P2",
                "protein_ref": "protein:P2",
                "leakage_key": "protein:P2",
                "linked_group_id": "protein:P2",
                "lane_depth": 1,
            },
        ]
    }
    simulation = {
        "simulation": {
            "assignments": [
                {
                    "canonical_id": "protein:P1",
                    "split_name": "train",
                    "linked_group_id": "protein:P1",
                },
                {
                    "canonical_id": "protein_variant:protein:P1:A10V",
                    "split_name": "train",
                    "linked_group_id": "protein:P1",
                },
                {
                    "canonical_id": "protein:P2",
                    "split_name": "test",
                    "linked_group_id": "protein:P2",
                },
            ]
        }
    }
    candidates_path = tmp_path / "entity_split_candidate_preview.json"
    simulation_path = tmp_path / "entity_split_simulation_preview.json"
    output_json = tmp_path / "entity_split_assignment_preview.json"
    output_md = tmp_path / "entity_split_assignment_preview.md"
    candidates_path.write_text(json.dumps(candidates), encoding="utf-8")
    simulation_path.write_text(json.dumps(simulation), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_entity_split_assignment_preview.py"),
            "--entity-split-candidates",
            str(candidates_path),
            "--entity-split-simulation",
            str(simulation_path),
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
    assert payload["group_row_count"] == 2
    assert payload["summary"]["split_group_counts"] == {"train": 1, "test": 1}
    assert payload["group_rows"][0]["linked_group_id"] in {"protein:P1", "protein:P2"}
    assert payload["truth_boundary"]["final_split_committed"] is False
    assert "Entity Split Assignment Preview" in output_md.read_text(encoding="utf-8")
