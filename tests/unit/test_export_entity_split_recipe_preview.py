from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_entity_split_recipe_preview(tmp_path: Path) -> None:
    contract = {
        "first_executable_recipe": {
            "recipe_id": "protein_spine_first_split_recipe_v1",
            "input_artifact": "entity_split_candidate_preview",
            "input_row_type": "entity_signature_row",
            "atomic_unit": "entity_signature_row",
            "hard_grouping": {
                "primary_group": "protein_spine_group",
                "secondary_hard_groups": ["exact_entity_group", "variant_delta_group"],
            },
            "soft_axes": ["taxon_group"],
            "reserved_null_axes": ["ligand_identity_group", "binding_context_group"],
            "allowed_entity_families": ["protein", "protein_variant", "structure_unit"],
            "execution_steps": ["load rows", "group by spine"],
            "success_criteria": ["no leakage"],
        },
        "preview_surface": {
            "row_count": 10,
            "linked_group_count": 3,
        },
    }
    simulation = {
        "summary": {
            "assignment_count": 10,
            "rejected_count": 0,
            "split_counts": {"train": 6, "val": 2, "test": 2},
            "target_counts": {"train": 7, "val": 1, "test": 2},
        }
    }
    contract_path = tmp_path / "recipe_contract.json"
    simulation_path = tmp_path / "entity_split_simulation_preview.json"
    output_json = tmp_path / "entity_split_recipe_preview.json"
    output_md = tmp_path / "entity_split_recipe_preview.md"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    simulation_path.write_text(json.dumps(simulation), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_entity_split_recipe_preview.py"),
            "--recipe-contract",
            str(contract_path),
            "--simulation-preview",
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
    assert payload["recipe"]["recipe_id"] == "protein_spine_first_split_recipe_v1"
    assert payload["grounding"]["candidate_row_count"] == 10
    assert payload["grounding"]["simulation_assignment_count"] == 10
    assert payload["truth_boundary"]["final_split_committed"] is False
    assert payload["truth_boundary"]["ready_for_recipe_export"] is True
    assert "Entity Split Recipe Preview" in output_md.read_text(encoding="utf-8")
