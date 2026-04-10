from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENTITY_SPLIT_CANDIDATES = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_candidate_preview.json"
)
DEFAULT_ENTITY_SPLIT_SIMULATION = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_simulation_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_assignment_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "entity_split_assignment_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_entity_split_assignment_preview(
    entity_split_candidates: dict[str, Any],
    entity_split_simulation: dict[str, Any],
) -> dict[str, Any]:
    candidate_rows = entity_split_candidates.get("candidate_rows", [])
    rows_by_id = {row["canonical_id"]: row for row in candidate_rows}
    grouped: dict[str, dict[str, Any]] = {}
    split_group_counts: dict[str, int] = defaultdict(int)

    for assignment in entity_split_simulation["simulation"]["assignments"]:
        canonical_id = assignment["canonical_id"]
        row = rows_by_id[canonical_id]
        linked_group_id = assignment["linked_group_id"]
        split_name = assignment["split_name"]

        existing = grouped.get(linked_group_id)
        if existing is None:
            existing = {
                "linked_group_id": linked_group_id,
                "split_name": split_name,
                "entity_count": 0,
                "entity_family_counts": defaultdict(int),
                "max_lane_depth": 0,
                "representative_accession": row["accession"],
                "canonical_ids": [],
            }
            grouped[linked_group_id] = existing
            split_group_counts[split_name] += 1
        elif existing["split_name"] != split_name:
            raise ValueError(
                f"linked group {linked_group_id} diverged across splits: "
                f"{existing['split_name']} vs {split_name}"
            )

        existing["entity_count"] += 1
        existing["entity_family_counts"][row["entity_family"]] += 1
        existing["max_lane_depth"] = max(existing["max_lane_depth"], row["lane_depth"])
        existing["canonical_ids"].append(canonical_id)

    group_rows = sorted(
        (
            {
                **row,
                "entity_family_counts": dict(row["entity_family_counts"]),
                "canonical_ids": sorted(row["canonical_ids"]),
            }
            for row in grouped.values()
        ),
        key=lambda item: (item["split_name"], -item["entity_count"], item["linked_group_id"]),
    )

    return {
        "artifact_id": "entity_split_assignment_preview",
        "schema_id": "proteosphere-entity-split-assignment-preview-2026-04-01",
        "status": "complete",
        "group_row_count": len(group_rows),
        "group_rows": group_rows,
        "summary": {
            "candidate_row_count": len(candidate_rows),
            "assignment_count": len(entity_split_simulation["simulation"]["assignments"]),
            "split_group_counts": dict(split_group_counts),
            "largest_groups": [
                {
                    "linked_group_id": row["linked_group_id"],
                    "split_name": row["split_name"],
                    "entity_count": row["entity_count"],
                }
                for row in sorted(
                    group_rows,
                    key=lambda item: (-item["entity_count"], item["linked_group_id"]),
                )[:10]
            ],
        },
        "truth_boundary": {
            "summary": (
                "This is a dry-run linked-group split assignment surface derived from the "
                "current entity split simulation. It shows how protein spine groups are "
                "currently assigned, but it does not commit a release split or CV fold set."
            ),
            "final_split_committed": False,
            "ready_for_fold_export": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Entity Split Assignment Preview",
        "",
        f"- Linked groups: `{payload['group_row_count']}`",
        f"- Candidate rows: `{summary['candidate_row_count']}`",
        f"- Assignments: `{summary['assignment_count']}`",
        "",
        "## Split Group Counts",
        "",
    ]
    for split_name, count in summary["split_group_counts"].items():
        lines.append(f"- `{split_name}`: `{count}` linked groups")
    lines.extend(["", "## Largest Groups", ""])
    for row in summary["largest_groups"]:
        lines.append(
            f"- `{row['linked_group_id']}` -> `{row['split_name']}` with "
            f"`{row['entity_count']}` entity rows"
        )
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a dry-run linked-group split assignment preview."
    )
    parser.add_argument(
        "--entity-split-candidates",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_CANDIDATES,
    )
    parser.add_argument(
        "--entity-split-simulation",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_SIMULATION,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_entity_split_assignment_preview(
        _read_json(args.entity_split_candidates),
        _read_json(args.entity_split_simulation),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
