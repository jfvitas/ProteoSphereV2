from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SINGLE_ACCESSION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_single_accession_preview.json"
)
DEFAULT_ANCHOR_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_anchor_validation.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "structure_followup_single_accession_validation_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "structure_followup_single_accession_validation_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_structure_followup_single_accession_validation_preview(
    single_accession_preview: dict[str, Any],
    anchor_validation: dict[str, Any],
) -> dict[str, Any]:
    selected_accession = single_accession_preview["selected_accession"]
    row_validation = next(
        row
        for row in anchor_validation.get("validated_rows", [])
        if row["accession"] == selected_accession
    )
    validation = anchor_validation["validation"]
    truth = single_accession_preview["truth_boundary"]
    return {
        "artifact_id": "structure_followup_single_accession_validation_preview",
        "schema_id": (
            "proteosphere-structure-followup-single-accession-validation-preview-2026-04-01"
        ),
        "status": "aligned",
        "selected_accession": selected_accession,
        "deferred_accession": single_accession_preview["deferred_accession"],
        "payload_row_count": single_accession_preview["payload_row_count"],
        "anchor_validation_status": anchor_validation["status"],
        "validated_row_count": validation["validated_row_count"],
        "candidate_variant_anchor_count_total": validation["candidate_variant_anchor_count"],
        "recommended_anchor_present_in_best_targets": row_validation[
            "recommended_anchor_present_in_best_targets"
        ],
        "variant_positions_within_recommended_span": row_validation[
            "variant_positions_within_recommended_span"
        ],
        "candidate_variant_anchor_count": row_validation["candidate_variant_anchor_count"],
        "candidate_only_no_variant_anchor": truth["candidate_only_no_variant_anchor"],
        "direct_structure_backed_join_certified": truth["direct_structure_backed_join_certified"],
        "ready_for_operator_preview": truth["ready_for_operator_preview"],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Structure Follow-up Single Accession Validation Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Selected accession: `{payload['selected_accession']}`",
        f"- Deferred accession: `{payload['deferred_accession']}`",
        f"- Anchor validation status: `{payload['anchor_validation_status']}`",
        f"- Candidate variant anchors: `{payload['candidate_variant_anchor_count']}`",
        "",
        "## Truth Boundary",
        "",
        "- This remains a candidate-only operator validation surface.",
        "- It does not certify a direct structure-backed join.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the structure follow-up single-accession validation preview."
    )
    parser.add_argument(
        "--single-accession-preview",
        type=Path,
        default=DEFAULT_SINGLE_ACCESSION_PREVIEW,
    )
    parser.add_argument(
        "--anchor-validation",
        type=Path,
        default=DEFAULT_ANCHOR_VALIDATION,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_followup_single_accession_validation_preview(
        _read_json(args.single_accession_preview),
        _read_json(args.anchor_validation),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
