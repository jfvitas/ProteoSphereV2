from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_pilot_preview.json"
)
DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_support_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_stage1_operator_queue_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_stage1_operator_queue_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_ligand_stage1_operator_queue_preview(
    ligand_identity_pilot_preview: dict[str, Any],
    ligand_support_readiness_preview: dict[str, Any],
) -> dict[str, Any]:
    support_rows = {
        row["accession"]: row for row in ligand_support_readiness_preview.get("rows", [])
    }
    ordered_rows = []
    for row in ligand_identity_pilot_preview.get("rows", []):
        support_row = support_rows[row["accession"]]
        ordered_rows.append(
            {
                "rank": row["rank"],
                "accession": row["accession"],
                "source_ref": row["source_ref"],
                "operator_label": row["pilot_role"],
                "pilot_lane_status": support_row["pilot_lane_status"],
                "current_blocker": support_row["current_blocker"],
                "next_truthful_stage": row["next_truthful_stage"],
            }
        )

    deferred_accession = ligand_identity_pilot_preview["deferred_accession"]
    return {
        "artifact_id": "ligand_stage1_operator_queue_preview",
        "schema_id": "proteosphere-ligand-stage1-operator-queue-preview-2026-04-01",
        "status": "complete",
        "surface_kind": "operator_preview_queue_card",
        "row_count": len(ordered_rows),
        "ordered_rows": ordered_rows,
        "deferred_row": {
            "accession": deferred_accession,
            "source_ref": f"ligand:{deferred_accession}",
            "operator_label": "deferred_accession",
            "next_truthful_stage": ligand_identity_pilot_preview["deferred_reason"],
        },
        "truth_boundary": {
            "summary": (
                "This is an operator-visible queue preview for the narrow ligand stage-1 "
                "ordering. It remains report-only, does not materialize ligand rows, does "
                "not imply ligand bundle inclusion, and keeps Q9UCM0 deferred."
            ),
            "report_only": True,
            "ligand_rows_materialized": False,
            "bundle_ligands_included": False,
            "q9ucm0_deferred": True,
            "ready_for_operator_preview": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ligand Stage-1 Operator Queue Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Surface kind: `{payload['surface_kind']}`",
        f"- Ordered rows: `{payload['row_count']}`",
        f"- Deferred accession: `{payload['deferred_row']['accession']}`",
        "",
        "## Queue Rows",
        "",
    ]
    for row in payload["ordered_rows"]:
        lines.append(
            f"- `{row['rank']}` `{row['accession']}` -> "
            f"`{row['operator_label']}` / `{row['pilot_lane_status']}` / "
            f"`{row['next_truthful_stage']}`"
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the operator-visible ligand stage-1 queue preview."
    )
    parser.add_argument(
        "--ligand-identity-pilot-preview",
        type=Path,
        default=DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW,
    )
    parser.add_argument(
        "--ligand-support-readiness-preview",
        type=Path,
        default=DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_stage1_operator_queue_preview(
        _read_json(args.ligand_identity_pilot_preview),
        _read_json(args.ligand_support_readiness_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

