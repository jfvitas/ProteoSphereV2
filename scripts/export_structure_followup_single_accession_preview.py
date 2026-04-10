from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMOTION_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "p76_structure_followup_next_single_accession_plan.json"
)
DEFAULT_PAYLOAD_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_payload_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_single_accession_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "structure_followup_single_accession_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_structure_followup_single_accession_preview(
    promotion_plan: dict[str, Any],
    payload_preview: dict[str, Any],
) -> dict[str, Any]:
    selected_accession = promotion_plan["promotion_plan"]["selected_accession"]
    deferred_accession = promotion_plan["promotion_plan"]["deferred_accession"]
    selected_row = next(
        row for row in payload_preview["payload_rows"] if row["accession"] == selected_accession
    )

    return {
        "artifact_id": "structure_followup_single_accession_preview",
        "schema_id": "proteosphere-structure-followup-single-accession-preview-2026-04-01",
        "status": "complete",
        "selected_accession": selected_accession,
        "deferred_accession": deferred_accession,
        "payload_row_count": 1,
        "payload_row": selected_row,
        "promotion_gate": promotion_plan["promotion_gate"],
        "operator_effect": promotion_plan["operator_effect"],
        "truth_boundary": {
            "summary": (
                "This is a single-accession narrowing of the existing structure follow-up "
                "payload preview for operator steering. It remains candidate-only and does "
                "not certify or promote a direct structure-backed join."
            ),
            "single_accession_scope": True,
            "candidate_only_no_variant_anchor": True,
            "direct_structure_backed_join_certified": False,
            "ready_for_operator_preview": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    row = payload["payload_row"]
    lines = [
        "# Structure Follow-Up Single Accession Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Selected accession: `{payload['selected_accession']}`",
        f"- Deferred accession: `{payload['deferred_accession']}`",
        f"- Variant ref: `{row['variant_ref']}`",
        f"- Structure ref: `{row['structure_id']}:{row['chain_id']}`",
        f"- Coverage: `{row['coverage']}`",
        "",
        "## Truth Boundary",
        "",
        f"- {payload['truth_boundary']['summary']}",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the single-accession structure follow-up preview."
    )
    parser.add_argument("--promotion-plan", type=Path, default=DEFAULT_PROMOTION_PLAN)
    parser.add_argument("--payload-preview", type=Path, default=DEFAULT_PAYLOAD_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_followup_single_accession_preview(
        _read_json(args.promotion_plan),
        _read_json(args.payload_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
