from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from datasets.recipes.schema import (  # noqa: E402
    RecipeCompletenessPolicy,
    RecipeLeakagePolicy,
    RecipeSelectionRule,
    TrainingRecipeSchema,
)
from datasets.recipes.split_simulator import simulate_recipe_splits  # noqa: E402

DEFAULT_ENTITY_SPLIT_CANDIDATES = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_candidate_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_simulation_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "entity_split_simulation_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_target_splits(candidate_rows: list[dict[str, Any]]) -> dict[str, int]:
    total = len(candidate_rows)
    train = int(total * 0.7)
    val = int(total * 0.15)
    test = total - train - val
    return {"train": train, "val": val, "test": test}


def build_recipe(candidate_rows: list[dict[str, Any]]) -> TrainingRecipeSchema:
    return TrainingRecipeSchema(
        recipe_id="recipe:entity-split-preview:v1",
        title="Entity split preview",
        goal=(
            "Preview leakage-safe splitting behavior across protein, variant, and "
            "structure entities using exact entity IDs and protein spine grouping."
        ),
        target_splits=_default_target_splits(candidate_rows),
        selection_rule=RecipeSelectionRule(
            field_name="canonical_id",
            operator="truthy",
            description="entity rows with canonical identifiers",
        ),
        completeness_policy=RecipeCompletenessPolicy(
            requested_modalities=(),
            max_missing_modalities=99,
            min_lane_depth=1,
            allow_thin_coverage=True,
            allow_mixed_evidence=True,
            require_packet_ready=False,
        ),
        leakage_policy=RecipeLeakagePolicy(
            scope="custom",
            key_field="leakage_key",
            forbid_cross_split=True,
        ),
        tags=("preview", "entity_split", "protein_spine_grouped"),
        notes=(
            "report-only split simulation preview",
            "ligand rows are not materialized yet",
            "protein_spine_group is the default hard linked group",
        ),
    )


def _family_counts_by_split(
    assignments: list[dict[str, Any]],
    candidate_rows_by_id: dict[str, dict[str, Any]],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for assignment in assignments:
        row = candidate_rows_by_id[assignment["canonical_id"]]
        counts[assignment["split_name"]][row["entity_family"]] += 1
    return {split: dict(values) for split, values in counts.items()}


def _largest_groups_by_split(
    assignments: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for assignment in assignments:
        grouped[assignment["split_name"]][assignment["linked_group_id"]] += 1
    output: dict[str, list[dict[str, Any]]] = {}
    for split_name, groups in grouped.items():
        output[split_name] = sorted(
            (
                {"linked_group_id": group_id, "entity_count": count}
                for group_id, count in groups.items()
            ),
            key=lambda item: (-item["entity_count"], item["linked_group_id"]),
        )[:10]
    return output


def build_entity_split_simulation_preview(
    entity_split_candidates: dict[str, Any],
) -> dict[str, Any]:
    candidate_rows = entity_split_candidates.get("candidate_rows", [])
    recipe = build_recipe(candidate_rows)
    result = simulate_recipe_splits(recipe, candidate_rows)
    result_dict = result.to_dict()
    candidate_rows_by_id = {
        row["canonical_id"]: row for row in candidate_rows
    }
    assignments = result_dict["assignments"]
    family_counts_by_split = _family_counts_by_split(assignments, candidate_rows_by_id)
    largest_groups_by_split = _largest_groups_by_split(assignments)

    return {
        "artifact_id": "entity_split_simulation_preview",
        "schema_id": "proteosphere-entity-split-simulation-preview-2026-04-01",
        "status": "complete",
        "recipe": recipe.to_dict(),
        "simulation": result_dict,
        "summary": {
            "candidate_row_count": len(candidate_rows),
            "assignment_count": len(assignments),
            "rejected_count": len(result_dict["rejected"]),
            "split_counts": result_dict["split_counts"],
            "target_counts": result_dict["target_counts"],
            "family_counts_by_split": family_counts_by_split,
            "largest_groups_by_split": largest_groups_by_split,
            "notes": result_dict["notes"],
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only split simulation preview derived from the current "
                "entity split candidate surface. It shows how the present protein-spine "
                "grouping would behave, not a finalized train/val/test release split."
            ),
            "final_split_committed": False,
            "ligand_rows_materialized": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Entity Split Simulation Preview",
        "",
        f"- Candidate rows: `{summary['candidate_row_count']}`",
        f"- Assigned rows: `{summary['assignment_count']}`",
        f"- Rejected rows: `{summary['rejected_count']}`",
        "",
        "## Split Counts",
        "",
    ]
    for split_name, count in summary["split_counts"].items():
        target = summary["target_counts"].get(split_name)
        lines.append(f"- `{split_name}`: `{count}` of target `{target}`")
    lines.extend(["", "## Family Counts By Split", ""])
    for split_name, counts in summary["family_counts_by_split"].items():
        compact = ", ".join(f"{family}={count}" for family, count in sorted(counts.items()))
        lines.append(f"- `{split_name}`: {compact}")
    lines.extend(["", "## Truth Boundary", ""])
    lines.append(f"- {payload['truth_boundary']['summary']}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a first split simulation preview from entity split candidates."
    )
    parser.add_argument(
        "--entity-split-candidates",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_CANDIDATES,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_entity_split_simulation_preview(
        _read_json(args.entity_split_candidates),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
