from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_split_engine_input_preview(tmp_path: Path) -> None:
    recipe_preview = {
        "recipe": {
            "recipe_id": "protein_spine_first_split_recipe_v1",
            "input_artifact": "entity_split_candidate_preview",
            "atomic_unit": "entity_signature_row",
            "hard_grouping": {
                "primary_group": "protein_spine_group",
                "secondary_hard_groups": ["exact_entity_group", "variant_delta_group"],
            },
            "allowed_entity_families": ["protein", "protein_variant", "structure_unit"],
            "reserved_null_axes": ["ligand_identity_group", "binding_context_group"],
        },
        "truth_boundary": {
            "ready_for_recipe_export": True,
        },
    }
    assignment_preview = {
        "group_row_count": 2,
        "group_rows": [
            {
                "linked_group_id": "protein:P1",
                "split_name": "train",
                "entity_count": 4,
            },
            {
                "linked_group_id": "protein:P2",
                "split_name": "test",
                "entity_count": 2,
            },
        ],
        "summary": {
            "candidate_row_count": 6,
            "assignment_count": 6,
            "split_group_counts": {"train": 1, "test": 1},
            "largest_groups": [
                {"linked_group_id": "protein:P1", "split_name": "train", "entity_count": 4}
            ],
        },
        "truth_boundary": {
            "ready_for_fold_export": False,
        },
    }
    ligand_row_preview = {
        "row_count": 3,
        "summary": {
            "grounded_accessions": ["P00387"],
            "candidate_only_accessions": ["Q9NZD4"],
        },
        "truth_boundary": {
            "ligand_rows_materialized": True,
        },
    }
    motif_domain_preview = {
        "row_count": 12,
        "truth_boundary": {
            "ready_for_bundle_preview": True,
            "governing_for_split_or_leakage": False,
        },
    }
    interaction_similarity_preview = {
        "row_count": 2,
        "summary": {
            "candidate_only_row_count": 2,
        },
        "truth_boundary": {
            "ready_for_bundle_preview": False,
            "candidate_only_rows": True,
        },
    }
    recipe_path = tmp_path / "entity_split_recipe_preview.json"
    assignment_path = tmp_path / "entity_split_assignment_preview.json"
    ligand_row_path = tmp_path / "ligand_row_materialization_preview.json"
    motif_domain_path = tmp_path / "motif_domain_compact_preview_family.json"
    interaction_similarity_path = tmp_path / "interaction_similarity_signature_preview.json"
    output_json = tmp_path / "split_engine_input_preview.json"
    output_md = tmp_path / "split_engine_input_preview.md"
    recipe_path.write_text(json.dumps(recipe_preview), encoding="utf-8")
    assignment_path.write_text(json.dumps(assignment_preview), encoding="utf-8")
    ligand_row_path.write_text(json.dumps(ligand_row_preview), encoding="utf-8")
    motif_domain_path.write_text(json.dumps(motif_domain_preview), encoding="utf-8")
    interaction_similarity_path.write_text(
        json.dumps(interaction_similarity_preview),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_split_engine_input_preview.py"),
            "--entity-split-recipe-preview",
            str(recipe_path),
            "--entity-split-assignment-preview",
            str(assignment_path),
            "--ligand-row-preview",
            str(ligand_row_path),
            "--motif-domain-preview",
            str(motif_domain_path),
            "--interaction-similarity-preview",
            str(interaction_similarity_path),
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
    assert payload["recipe_binding"]["recipe_id"] == "protein_spine_first_split_recipe_v1"
    assert payload["assignment_binding"]["group_row_count"] == 2
    assert payload["execution_readiness"]["recipe_ready"] is True
    assert payload["execution_readiness"]["fold_export_ready"] is False
    assert payload["execution_readiness"]["supplemental_non_governing_preview_ready"] is True
    assert payload["execution_readiness"]["ligand_governing_split_ready"] is False
    assert payload["supplemental_non_governing_signals"]["ligand_rows"]["status"] == (
        "available_non_governing"
    )
    assert payload["supplemental_non_governing_signals"]["motif_domain_compact"]["status"] == (
        "available_non_governing"
    )
    assert (
        payload["supplemental_non_governing_signals"]["interaction_similarity_preview"][
            "status"
        ]
        == "blocked_candidate_only"
    )
    assert payload["truth_boundary"]["ready_for_split_engine_dry_run"] is True
    assert "Split Engine Input Preview" in output_md.read_text(encoding="utf-8")
