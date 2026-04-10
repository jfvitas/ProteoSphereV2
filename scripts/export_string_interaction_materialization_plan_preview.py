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
DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_freeze_gate_preview.json"
)
DEFAULT_PROCUREMENT_SOURCE_COMPLETION = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_BROAD_MIRROR_PROGRESS = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_progress.json"
)
DEFAULT_BROAD_MIRROR_REMAINING_TRANSFER_STATUS = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
)
DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "string_interaction_materialization_plan_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "string_interaction_materialization_plan_preview.md"
)


def build_string_interaction_materialization_plan_preview(
    procurement_tail_freeze_gate: dict[str, Any],
    procurement_source_completion: dict[str, Any],
    broad_mirror_progress: dict[str, Any],
    broad_mirror_remaining_transfer_status: dict[str, Any],
    interaction_similarity_signature_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = interaction_similarity_signature_preview.get("rows") or []
    accessions = sorted(
        {
            str(
                row.get("accession")
                or row.get("protein_accession")
                or row.get("protein_id")
                or ""
            ).strip()
            for row in rows
            if isinstance(row, dict)
        }
        - {""}
    )
    remaining_files = [
        str(item.get("relative_path") or item.get("file") or item.get("filename") or "").strip()
        for item in (
            broad_mirror_remaining_transfer_status.get("actively_transferring_now")
            or broad_mirror_remaining_transfer_status.get("active_rows")
            or broad_mirror_remaining_transfer_status.get("rows")
            or []
        )
        if isinstance(item, dict)
    ]
    remaining_files = [item for item in remaining_files if item]
    string_source_row = next(
        (
            source
            for source in (broad_mirror_progress.get("sources") or [])
            if isinstance(source, dict) and source.get("source_id") == "string"
        ),
        {},
    )
    string_ready = bool(procurement_source_completion.get("string_completion_ready"))
    uniref_ready = bool(procurement_source_completion.get("uniprot_completion_ready"))
    materialization_state = (
        "ready_to_materialize_from_string_complete"
        if string_ready
        else procurement_tail_freeze_gate.get("gate_status")
    )
    return {
        "artifact_id": "string_interaction_materialization_plan_preview",
        "schema_id": "proteosphere-string-interaction-materialization-plan-preview-2026-04-02",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "mirror_completion_status": materialization_state,
        "remaining_gap_file_count": procurement_tail_freeze_gate.get(
            "remaining_gap_file_count"
        ),
        "tracked_remaining_transfer_files": remaining_files,
        "supported_accession_count": len(accessions),
        "supported_accessions": accessions,
        "current_interaction_preview_status": interaction_similarity_signature_preview.get(
            "status"
        ),
        "planned_families": [
            {
                "family_id": "string_interaction_compact_preview",
                "planned_status": "grounded_preview_safe_after_tail_validation",
                "row_shape": [
                    "accession",
                    "partner_count",
                    "max_score",
                    "mean_score",
                    "evidence_channel_presence_flags",
                ],
            },
            {
                "family_id": "string_evidence_channel_rollup_preview",
                "planned_status": "report_only_non_governing_until_direct_validation",
                "channels": [
                    "experimental",
                    "database",
                    "textmining",
                    "coexpression",
                    "neighborhood",
                    "fusion",
                    "cooccurrence",
                ],
            },
            {
                "family_id": "interaction_partner_context_preview",
                "planned_status": "report_only_non_governing",
                "purpose": "Top partners and evidence-origin context for in-scope accessions.",
            },
        ],
        "planned_join_route": {
            "source_alias_tables_required": True,
            "accession_to_string_id": "required_before_direct_edge_materialization",
            "project_to_structure_chains_later": True,
        },
        "forecast": {
            "interaction_readiness_before_tail": (
                "support-only non-governing string-ready"
                if string_ready
                else "candidate-only non-governing"
            ),
            "interaction_readiness_after_tail_validation": (
                "support-only non-governing string-ready"
                if string_ready
                else "grounded preview-safe"
            ),
            "evidence_channel_separation_required": True,
            "transferred_evidence_separate_non_governing_subfamily": True,
            "text_mining_default_non_governing": True,
            "string_completion_ready": string_ready,
            "uniref_completion_ready": uniref_ready,
        },
        "source_context": {
            "broad_mirror_percent_complete": string_source_row.get("coverage_percent"),
            "broad_mirror_status": string_source_row.get("status")
            or broad_mirror_progress.get("status"),
            "procurement_gate_status": materialization_state,
        },
        "truth_boundary": {
            "summary": (
                "This is a forecast and materialization plan only. It does not materialize "
                "STRING rows, does not alter split/leakage behavior, and keeps STRING "
                "non-governing even when the STRING source-specific gate is complete."
            ),
            "report_only": True,
            "materialization_started": False,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# STRING Interaction Materialization Plan Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Mirror gate: `{payload['mirror_completion_status']}`",
        (
            "- Supported accessions in current preview overlap: "
            f"`{payload['supported_accession_count']}`"
        ),
        "",
    ]
    for family in payload["planned_families"]:
        lines.append(
            f"- `{family['family_id']}` / `{family['planned_status']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only STRING interaction materialization plan preview."
    )
    parser.add_argument(
        "--procurement-tail-freeze-gate",
        type=Path,
        default=DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE,
    )
    parser.add_argument(
        "--procurement-source-completion",
        type=Path,
        default=DEFAULT_PROCUREMENT_SOURCE_COMPLETION,
    )
    parser.add_argument(
        "--broad-mirror-progress",
        type=Path,
        default=DEFAULT_BROAD_MIRROR_PROGRESS,
    )
    parser.add_argument(
        "--broad-mirror-remaining-transfer-status",
        type=Path,
        default=DEFAULT_BROAD_MIRROR_REMAINING_TRANSFER_STATUS,
    )
    parser.add_argument(
        "--interaction-similarity-signature-preview",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_string_interaction_materialization_plan_preview(
        read_json(args.procurement_tail_freeze_gate),
        read_json(args.procurement_source_completion),
        read_json(args.broad_mirror_progress),
        read_json(args.broad_mirror_remaining_transfer_status),
        read_json(args.interaction_similarity_signature_preview),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
