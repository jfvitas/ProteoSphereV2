from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_split_engine_dry_run(tmp_path: Path) -> None:
    split_engine_input_preview = {
        "recipe_binding": {
            "recipe_id": "protein_spine_first_split_recipe_v1",
            "input_artifact": "entity_split_candidate_preview",
        },
        "assignment_binding": {
            "candidate_row_count": 29,
            "assignment_count": 29,
            "split_group_counts": {"train": 1, "val": 1, "test": 2},
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 10},
                {"linked_group_id": "protein:P68871", "split_name": "val", "entity_count": 8},
                {"linked_group_id": "protein:P69905", "split_name": "test", "entity_count": 6},
                {"linked_group_id": "protein:P31749", "split_name": "test", "entity_count": 5},
            ],
        },
    }
    assignment_preview = {
        "group_rows": [
            {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 10},
            {"linked_group_id": "protein:P68871", "split_name": "val", "entity_count": 8},
            {"linked_group_id": "protein:P69905", "split_name": "test", "entity_count": 6},
            {"linked_group_id": "protein:P31749", "split_name": "test", "entity_count": 5},
        ],
        "summary": {
            "assignment_count": 29,
            "split_group_counts": {"train": 1, "val": 1, "test": 2},
        }
    }
    simulation_preview = {
        "recipe": {
            "recipe_id": "recipe:entity-split-preview:v1",
        },
        "summary": {
            "candidate_row_count": 29,
            "assignment_count": 29,
            "split_counts": {"train": 10, "val": 8, "test": 11},
        },
    }
    input_path = tmp_path / "split_engine_input_preview.json"
    assignment_path = tmp_path / "entity_split_assignment_preview.json"
    simulation_path = tmp_path / "entity_split_simulation_preview.json"
    output_json = tmp_path / "split_engine_dry_run_validation.json"
    output_md = tmp_path / "split_engine_dry_run_validation.md"
    input_path.write_text(json.dumps(split_engine_input_preview), encoding="utf-8")
    assignment_path.write_text(json.dumps(assignment_preview), encoding="utf-8")
    simulation_path.write_text(json.dumps(simulation_preview), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_split_engine_dry_run.py"),
            "--split-engine-input-preview",
            str(input_path),
            "--entity-split-assignment-preview",
            str(assignment_path),
            "--entity-split-simulation-preview",
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
    assert payload["status"] == "aligned"
    assert payload["validation"]["recipe_id"] == "protein_spine_first_split_recipe_v1"
    assert payload["validation"]["simulation_recipe_id"] == "recipe:entity-split-preview:v1"
    assert payload["validation"]["candidate_row_count"] == 29
    assert payload["validation"]["split_group_counts"] == {"train": 1, "val": 1, "test": 2}
    assert payload["validation"]["row_level_split_counts"] == {
        "train": 10,
        "val": 8,
        "test": 11,
    }
    assert payload["truth_boundary"]["final_split_committed"] is False
    assert "Split Engine Dry Run Validation" in output_md.read_text(encoding="utf-8")
