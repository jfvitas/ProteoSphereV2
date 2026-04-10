from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_ENTITY_SPLIT_ASSIGNMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_assignment_preview.json"
)
DEFAULT_ENTITY_SPLIT_SIMULATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_simulation_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_dry_run_validation.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_engine_dry_run_validation.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _compare_equal(
    *,
    label: str,
    left: Any,
    right: Any,
    issues: list[str],
    matches: list[str],
) -> None:
    if left == right:
        matches.append(label)
    else:
        issues.append(label)


def _row_level_split_counts(group_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in group_rows:
        split_name = row["split_name"]
        counts[split_name] = counts.get(split_name, 0) + int(row["entity_count"])
    return counts


def build_split_engine_dry_run_validation(
    split_engine_input_preview: dict[str, Any],
    entity_split_assignment_preview: dict[str, Any],
    entity_split_simulation_preview: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    matches: list[str] = []
    input_recipe = split_engine_input_preview["recipe_binding"]
    input_assignment = split_engine_input_preview["assignment_binding"]
    assignment_summary = entity_split_assignment_preview["summary"]
    simulation_summary = entity_split_simulation_preview["summary"]
    simulation_recipe = entity_split_simulation_preview["recipe"]
    row_level_split_counts = _row_level_split_counts(
        entity_split_assignment_preview["group_rows"]
    )

    _compare_equal(
        label="recipe_input_artifact",
        left=input_recipe["input_artifact"],
        right="entity_split_candidate_preview",
        issues=issues,
        matches=matches,
    )
    _compare_equal(
        label="candidate_row_count",
        left=input_assignment["candidate_row_count"],
        right=simulation_summary["candidate_row_count"],
        issues=issues,
        matches=matches,
    )
    _compare_equal(
        label="assignment_count",
        left=input_assignment["assignment_count"],
        right=assignment_summary["assignment_count"],
        issues=issues,
        matches=matches,
    )
    _compare_equal(
        label="assignment_vs_simulation_count",
        left=assignment_summary["assignment_count"],
        right=simulation_summary["assignment_count"],
        issues=issues,
        matches=matches,
    )
    _compare_equal(
        label="split_group_counts",
        left=input_assignment["split_group_counts"],
        right=assignment_summary["split_group_counts"],
        issues=issues,
        matches=matches,
    )
    _compare_equal(
        label="row_level_split_counts",
        left=row_level_split_counts,
        right={
            "train": simulation_summary["split_counts"]["train"],
            "val": simulation_summary["split_counts"]["val"],
            "test": simulation_summary["split_counts"]["test"],
        },
        issues=issues,
        matches=matches,
    )

    largest_groups = input_assignment["largest_groups"][:4]
    expected_largest = [
        {"linked_group_id": "protein:P04637", "split_name": "train"},
        {"linked_group_id": "protein:P68871", "split_name": "val"},
        {"linked_group_id": "protein:P69905", "split_name": "test"},
        {"linked_group_id": "protein:P31749", "split_name": "test"},
    ]
    largest_group_match = [
        {
            "linked_group_id": row["linked_group_id"],
            "split_name": row["split_name"],
        }
        for row in largest_groups
    ]
    _compare_equal(
        label="largest_group_order",
        left=largest_group_match,
        right=expected_largest,
        issues=issues,
        matches=matches,
    )

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "split_engine_dry_run_validation",
        "schema_id": "proteosphere-split-engine-dry-run-validation-2026-04-01",
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "validation": {
            "matches": matches,
            "issues": issues,
            "recipe_id": input_recipe["recipe_id"],
            "simulation_recipe_id": simulation_recipe["recipe_id"],
            "candidate_row_count": input_assignment["candidate_row_count"],
            "assignment_count": input_assignment["assignment_count"],
            "split_group_counts": input_assignment["split_group_counts"],
            "row_level_split_counts": row_level_split_counts,
            "largest_groups": largest_groups,
        },
        "truth_boundary": {
            "summary": (
                "This validation checks parity across the current split-engine input, "
                "assignment preview, and simulation preview. It does not commit folds or "
                "promote a release split."
            ),
            "final_split_committed": False,
            "fold_export_ready": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    lines = [
        "# Split Engine Dry Run Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Recipe ID: `{validation['recipe_id']}`",
        f"- Candidate rows: `{validation['candidate_row_count']}`",
        f"- Assignment rows: `{validation['assignment_count']}`",
        "",
        "## Matches",
        "",
    ]
    for item in validation["matches"]:
        lines.append(f"- `{item}`")
    if validation["issues"]:
        lines.extend(["", "## Issues", ""])
        for item in validation["issues"]:
            lines.append(f"- `{item}`")
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate parity across current split dry-run preview surfaces."
    )
    parser.add_argument(
        "--split-engine-input-preview",
        type=Path,
        default=DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW,
    )
    parser.add_argument(
        "--entity-split-assignment-preview",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_ASSIGNMENT_PREVIEW,
    )
    parser.add_argument(
        "--entity-split-simulation-preview",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_SIMULATION_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_split_engine_dry_run_validation(
        _read_json(args.split_engine_input_preview),
        _read_json(args.entity_split_assignment_preview),
        _read_json(args.entity_split_simulation_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
