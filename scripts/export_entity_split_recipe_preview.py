from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p64_first_split_recipe_contract.json"
)
DEFAULT_SIMULATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_simulation_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_recipe_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "entity_split_recipe_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_entity_split_recipe_preview(
    recipe_contract: dict[str, Any],
    simulation_preview: dict[str, Any],
) -> dict[str, Any]:
    recipe = recipe_contract["first_executable_recipe"]
    simulation_summary = simulation_preview["summary"]
    contract_preview = recipe_contract["preview_surface"]

    return {
        "artifact_id": "entity_split_recipe_preview",
        "schema_id": "proteosphere-entity-split-recipe-preview-2026-04-01",
        "status": "complete",
        "recipe": {
            "recipe_id": recipe["recipe_id"],
            "input_artifact": recipe["input_artifact"],
            "input_row_type": recipe["input_row_type"],
            "atomic_unit": recipe["atomic_unit"],
            "hard_grouping": recipe["hard_grouping"],
            "soft_axes": recipe["soft_axes"],
            "reserved_null_axes": recipe["reserved_null_axes"],
            "allowed_entity_families": recipe["allowed_entity_families"],
            "execution_steps": recipe["execution_steps"],
            "success_criteria": recipe["success_criteria"],
        },
        "grounding": {
            "candidate_row_count": contract_preview["row_count"],
            "linked_group_count": contract_preview["linked_group_count"],
            "simulation_assignment_count": simulation_summary["assignment_count"],
            "simulation_rejected_count": simulation_summary["rejected_count"],
            "simulation_split_counts": simulation_summary["split_counts"],
            "simulation_target_counts": simulation_summary["target_counts"],
        },
        "truth_boundary": {
            "summary": (
                "This recipe preview is a compact executable-facing view of the current "
                "first split recipe contract. It is grounded in the live split simulation, "
                "but it does not commit a release split or materialize ligand-aware axes."
            ),
            "final_split_committed": False,
            "ligand_axes_materialized": False,
            "report_only_basis_contract": True,
            "ready_for_recipe_export": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    recipe = payload["recipe"]
    grounding = payload["grounding"]
    lines = [
        "# Entity Split Recipe Preview",
        "",
        f"- Recipe ID: `{recipe['recipe_id']}`",
        f"- Input artifact: `{recipe['input_artifact']}`",
        f"- Atomic unit: `{recipe['atomic_unit']}`",
        f"- Primary hard group: `{recipe['hard_grouping']['primary_group']}`",
        "",
        "## Grounding",
        "",
        f"- Candidate rows: `{grounding['candidate_row_count']}`",
        f"- Linked groups: `{grounding['linked_group_count']}`",
        f"- Simulation assignments: `{grounding['simulation_assignment_count']}`",
        f"- Simulation rejected rows: `{grounding['simulation_rejected_count']}`",
        "",
        "## Allowed Families",
        "",
    ]
    for family in recipe["allowed_entity_families"]:
        lines.append(f"- `{family}`")
    lines.extend(["", "## Reserved Null Axes", ""])
    for axis in recipe["reserved_null_axes"]:
        lines.append(f"- `{axis}`")
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a live recipe preview grounded in the split recipe contract."
    )
    parser.add_argument("--recipe-contract", type=Path, default=DEFAULT_RECIPE_CONTRACT)
    parser.add_argument(
        "--simulation-preview",
        type=Path,
        default=DEFAULT_SIMULATION_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_entity_split_recipe_preview(
        _read_json(args.recipe_contract),
        _read_json(args.simulation_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
