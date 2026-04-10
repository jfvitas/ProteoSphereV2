from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
)
DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_validation.json"
)
DEFAULT_INTERACTION_SIMILARITY_OPERATOR_HANDOFF = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_operator_handoff.json"
)
DEFAULT_STRING_INTERACTION_MATERIALIZATION_PLAN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "string_interaction_materialization_plan_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_freeze_gate_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "interaction_string_merge_impact_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "interaction_string_merge_impact_preview.md"


def _coalesce_text(*values: Any, default: str = "") -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return default


def build_interaction_string_merge_impact_preview(
    interaction_similarity_signature_preview: dict[str, Any],
    interaction_similarity_signature_validation: dict[str, Any],
    interaction_similarity_operator_handoff: dict[str, Any],
    string_interaction_materialization_plan_preview: dict[str, Any],
    procurement_tail_freeze_gate_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = interaction_similarity_signature_preview.get("rows") or []
    summary = interaction_similarity_signature_preview.get("summary") or {}
    source_surfaces = interaction_similarity_signature_preview.get("source_surfaces") or {}
    validation_truth = interaction_similarity_signature_validation.get("truth_boundary") or {}
    handoff_state = interaction_similarity_operator_handoff.get("current_state") or {}
    handoff_truth = interaction_similarity_operator_handoff.get("truth_boundary") or {}
    plan_forecast = string_interaction_materialization_plan_preview.get("forecast") or {}
    gate_truth = procurement_tail_freeze_gate_preview.get("truth_boundary") or {}

    accession_set = sorted(
        {str(row.get("accession") or "").strip() for row in rows if isinstance(row, dict)} - {""}
    )

    candidate_only_row_count = int(summary.get("candidate_only_row_count") or 0)
    bundle_included = bool(
        interaction_similarity_signature_preview.get("bundle_alignment", {}).get(
            "interaction_similarity_signatures_included"
        )
    )
    bundle_record_count = int(
        interaction_similarity_signature_preview.get("bundle_alignment", {}).get(
            "interaction_similarity_signatures_record_count"
        )
        or 0
    )
    string_surface_state = _coalesce_text(
        source_surfaces.get("string", {}).get("disk_state"),
        handoff_state.get("string_surface_state"),
        default="unknown",
    )
    validation_status = _coalesce_text(
        interaction_similarity_signature_validation.get("status"),
        default="unknown",
    )
    preview_status = _coalesce_text(
        interaction_similarity_signature_preview.get("status"),
        default="unknown",
    )
    gate_status = _coalesce_text(procurement_tail_freeze_gate_preview.get("gate_status"))
    plan_status = _coalesce_text(string_interaction_materialization_plan_preview.get("status"))

    current_state = {
        "preview_status": preview_status,
        "validation_status": validation_status,
        "preview_row_count": int(interaction_similarity_signature_preview.get("row_count") or 0),
        "candidate_only_row_count": candidate_only_row_count,
        "source_overlap_accessions": summary.get("source_overlap_accessions") or accession_set,
        "biogrid_matched_row_total": int(summary.get("biogrid_matched_row_total") or 0),
        "string_surface_state": string_surface_state,
        "string_top_level_file_present_count": int(
            summary.get("string_top_level_file_present_count") or 0
        ),
        "string_top_level_file_partial_count": int(
            summary.get("string_top_level_file_partial_count") or 0
        ),
        "string_top_level_file_missing_count": int(
            summary.get("string_top_level_file_missing_count") or 0
        ),
        "bundle_interaction_similarity_signatures_included": bundle_included,
        "bundle_interaction_similarity_signatures_record_count": bundle_record_count,
        "bundle_manifest_status": _coalesce_text(
            interaction_similarity_operator_handoff.get("current_state", {}).get(
                "bundle_manifest_status"
            ),
            default=_coalesce_text(
                interaction_similarity_signature_preview.get("bundle_alignment", {}).get(
                    "bundle_status"
                ),
                default="unknown",
            ),
        ),
        "planned_string_materialization_status": plan_status,
        "planned_string_supported_accession_count": int(
            string_interaction_materialization_plan_preview.get("supported_accession_count") or 0
        ),
        "planned_string_readiness_before_tail": _coalesce_text(
            plan_forecast.get("interaction_readiness_before_tail"), default="unknown"
        ),
        "planned_string_readiness_after_tail_validation": _coalesce_text(
            plan_forecast.get("interaction_readiness_after_tail_validation"),
            default="unknown",
        ),
        "procurement_gate_status": gate_status,
        "remaining_gap_file_count": int(
            procurement_tail_freeze_gate_preview.get("remaining_gap_file_count") or 0
        ),
        "string_complete": bool(
            procurement_tail_freeze_gate_preview.get("freeze_conditions", {}).get("string_complete")
        ),
        "uniprot_complete": bool(
            procurement_tail_freeze_gate_preview.get("freeze_conditions", {}).get(
                "uniprot_complete"
            )
        ),
    }

    merge_impact = {
        "interaction_family_materialized": bool(
            interaction_similarity_signature_preview.get("truth_boundary", {}).get(
                "interaction_family_materialized"
            )
        ),
        "string_family_materialized": bool(
            interaction_similarity_signature_preview.get("truth_boundary", {}).get(
                "string_family_materialized"
            )
        ),
        "merge_changes_split_or_leakage": False,
        "bundle_safe_immediately": bool(handoff_truth.get("bundle_safe_immediately"))
        or bool(validation_truth.get("bundle_safe_immediately")),
        "direct_interaction_family_claimed": bool(
            interaction_similarity_signature_preview.get("truth_boundary", {}).get(
                "direct_interaction_family_claimed"
            )
        ),
        "direct_string_family_claimed": False,
        "report_only_non_governing": True,
        "non_governing_until_tail_completion": True,
        "procurement_tail_completion_required": bool(
            gate_truth.get("freeze_requires_zero_gap", True)
        ),
        "next_safe_step": (
            "Keep interaction similarity report-only and non-governing; do not "
            "promote STRING into split or leakage governance until the procurement "
            "tail freeze gate clears."
        ),
        "why": [
            "The compact interaction preview is candidate-only and already marked report-only.",
            "STRING remains partial on disk and not registry-present in the current lane.",
            "The procurement tail freeze gate is still blocked_pending_zero_gap.",
            (
                "The STRING materialization plan forecast is still candidate-only "
                "non-governing before tail validation."
            ),
        ],
    }

    return {
        "artifact_id": "interaction_string_merge_impact_preview",
        "schema_id": "proteosphere-interaction-string-merge-impact-preview-2026-04-03",
        "status": "report_only",
        "report_type": "interaction_string_merge_impact_preview",
        "policy_family": "interaction_similarity_compact_family",
        "policy_label": "report_only_non_governing",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_artifacts": {
            "interaction_similarity_signature_preview": (
                "artifacts/status/interaction_similarity_signature_preview.json"
            ),
            "interaction_similarity_signature_validation": (
                "artifacts/status/interaction_similarity_signature_validation.json"
            ),
            "interaction_similarity_operator_handoff": (
                "artifacts/status/interaction_similarity_operator_handoff.json"
            ),
            "string_interaction_materialization_plan_preview": (
                "artifacts/status/string_interaction_materialization_plan_preview.json"
            ),
            "procurement_tail_freeze_gate_preview": (
                "artifacts/status/procurement_tail_freeze_gate_preview.json"
            ),
        },
        "current_state": current_state,
        "merge_impact": merge_impact,
        "operator_summary": {
            "headline": (
                "STRING merge impact remains report-only and non-governing until the "
                "procurement tail is complete."
            ),
            "compact_summary": (
                "BioGRID and IntAct support the current interaction preview, STRING is "
                "still partial on disk, validation is aligned, and the tail freeze gate "
                "is still blocked_pending_zero_gap. The merge changes no split or leakage "
                "claims today."
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only impact preview for the STRING merge lane. It does "
                "not materialize STRING rows, does not change split or leakage claims, and "
                "does not become governing until the procurement tail freeze gate clears."
            ),
            "report_only": True,
            "interaction_family_materialized": bool(
                interaction_similarity_signature_preview.get("truth_boundary", {}).get(
                    "interaction_family_materialized"
                )
            ),
            "string_family_materialized": bool(
                interaction_similarity_signature_preview.get("truth_boundary", {}).get(
                    "string_family_materialized"
                )
            ),
            "merge_changes_split_or_leakage": False,
            "bundle_safe_immediately": bool(handoff_truth.get("bundle_safe_immediately"))
            or bool(validation_truth.get("bundle_safe_immediately")),
            "procurement_tail_completion_required": bool(
                gate_truth.get("freeze_requires_zero_gap", True)
            ),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    current = payload["current_state"]
    merge = payload["merge_impact"]
    lines = [
        "# Interaction STRING Merge Impact Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Policy label: `{payload['policy_label']}`",
        f"- Preview rows: `{current['preview_row_count']}`",
        f"- Candidate-only rows: `{current['candidate_only_row_count']}`",
        f"- STRING surface state: `{current['string_surface_state']}`",
        f"- Procurement gate: `{current['procurement_gate_status']}`",
        "",
        "## Merge Impact",
        "",
        f"- Merge changes split or leakage: `{merge['merge_changes_split_or_leakage']}`",
        f"- Bundle safe immediately: `{merge['bundle_safe_immediately']}`",
        f"- Non-governing until tail completion: `{merge['non_governing_until_tail_completion']}`",
        (
            "- Procurement tail completion required: "
            f"`{merge['procurement_tail_completion_required']}`"
        ),
        "",
        "## Truth Boundary",
        "",
        f"- {payload['truth_boundary']['summary']}",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only STRING merge impact preview."
    )
    parser.add_argument(
        "--interaction-similarity-signature-preview",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--interaction-similarity-signature-validation",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_VALIDATION,
    )
    parser.add_argument(
        "--interaction-similarity-operator-handoff",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY_OPERATOR_HANDOFF,
    )
    parser.add_argument(
        "--string-interaction-materialization-plan-preview",
        type=Path,
        default=DEFAULT_STRING_INTERACTION_MATERIALIZATION_PLAN_PREVIEW,
    )
    parser.add_argument(
        "--procurement-tail-freeze-gate-preview",
        type=Path,
        default=DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_interaction_string_merge_impact_preview(
        read_json(args.interaction_similarity_signature_preview),
        read_json(args.interaction_similarity_signature_validation),
        read_json(args.interaction_similarity_operator_handoff),
        read_json(args.string_interaction_materialization_plan_preview),
        read_json(args.procurement_tail_freeze_gate_preview),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
