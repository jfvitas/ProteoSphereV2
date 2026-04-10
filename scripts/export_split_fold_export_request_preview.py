from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPL_ORDER_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p75_split_after_gate_check_impl_order.json"
)
DEFAULT_POST_STAGING_GATE_CHECK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_preview.json"
)
DEFAULT_POST_STAGING_GATE_CHECK_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_validation.json"
)
DEFAULT_STAGING_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_staging_preview.json"
)
DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_request_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_fold_export_request_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_split_fold_export_request_preview(
    impl_order_contract: dict[str, Any],
    post_staging_gate_check_preview: dict[str, Any],
    post_staging_gate_check_validation: dict[str, Any],
    staging_preview: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
    split_fold_export_materialization_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_stage = impl_order_contract["proposed_implementation_order"][0]
    live_grounding = impl_order_contract["current_live_grounding"]
    gate_check = post_staging_gate_check_preview["gate_check"]
    gate_check_stage = post_staging_gate_check_preview["stage"]
    gate_check_parity = post_staging_gate_check_preview["staging_parity"]
    gate_check_blocked = post_staging_gate_check_preview["blocked_report"]
    gate_check_validation = post_staging_gate_check_validation["validation"]
    staging_manifest = staging_preview["staging_manifest"]
    assignment_binding = split_engine_input_preview["assignment_binding"]
    recipe_binding = split_engine_input_preview["recipe_binding"]
    fold_export_materialized = bool(
        (split_fold_export_materialization_preview or {}).get("truth_boundary", {}).get(
            "cv_folds_materialized"
        )
    )

    request_manifest_id = (
        f"{request_stage['stage_id']}:{recipe_binding['recipe_id']}:"
        f"{assignment_binding['candidate_row_count']}"
    )

    return {
        "artifact_id": "split_fold_export_request_preview",
        "schema_id": "proteosphere-split-fold-export-request-preview-2026-04-01",
        "status": "complete" if fold_export_materialized else "blocked_report_emitted",
        "stage": {
            "stage_id": request_stage["stage_id"],
            "stage_shape": request_stage["stage_shape"],
            "purpose": request_stage["purpose"],
            "run_scoped_only": True,
            "today_status": "fulfilled" if fold_export_materialized else request_stage["today_status"],
        },
        "request_binding": {
            "request_manifest_id": request_manifest_id,
            "recipe_id": recipe_binding["recipe_id"],
            "input_artifact": recipe_binding["input_artifact"],
            "linked_group_count": assignment_binding["group_row_count"],
            "candidate_row_count": assignment_binding["candidate_row_count"],
            "assignment_count": assignment_binding["assignment_count"],
        },
        "request_manifest_preview": {
            "request_scope": "run_scoped_only",
            "gate_stage_id": gate_check_stage["stage_id"],
            "gate_status": "open" if fold_export_materialized else gate_check["gate_status"],
            "staging_status": gate_check_parity["staging_status"],
            "staging_validation_status": gate_check_parity["staging_validation_status"],
            "post_staging_validation_status": post_staging_gate_check_validation["status"],
            "split_group_counts": staging_manifest["split_group_counts"],
            "row_level_split_counts": staging_manifest["row_level_split_counts"],
            "largest_groups": staging_manifest["largest_groups"],
            "must_hold": request_stage["must_hold"],
        },
        "blocked_report": {
            "blocked": not fold_export_materialized,
            "blocked_reasons": [] if fold_export_materialized else gate_check_blocked["blocked_reasons"],
            "gate_validation_issue_count": len(gate_check_validation["issues"]),
            "post_staging_validation_status": post_staging_gate_check_validation["status"],
            "cv_fold_export_unlocked": fold_export_materialized or gate_check["cv_fold_export_unlocked"],
            "cv_folds_materialized": fold_export_materialized or gate_check_blocked["cv_folds_materialized"],
            "final_split_committed": gate_check_blocked["final_split_committed"],
        },
        "live_grounding": {
            "gate_status": "open" if fold_export_materialized else live_grounding["gate_status"],
            "dry_run_validation_status": live_grounding["dry_run_validation_status"],
            "candidate_row_count": live_grounding["candidate_row_count"],
            "assignment_count": live_grounding["assignment_count"],
            "split_group_counts": live_grounding["split_group_counts"],
            "row_level_split_counts": live_grounding["row_level_split_counts"],
        },
        "truth_boundary": {
            "summary": (
            "This request preview is the next run-scoped split handoff after the "
            "post-staging gate check. When a run-scoped fold export already exists, this "
            "surface reflects the fulfilled request without promoting a release split."
            ),
            "run_scoped_only": True,
            "cv_fold_export_unlocked": fold_export_materialized,
            "cv_folds_materialized": fold_export_materialized,
            "final_split_committed": False,
            "request_only_no_fold_materialization": not fold_export_materialized,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    stage = payload["stage"]
    binding = payload["request_binding"]
    manifest = payload["request_manifest_preview"]
    blocked = payload["blocked_report"]
    lines = [
        "# Split Fold Export Request Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Stage ID: `{stage['stage_id']}`",
        f"- Stage shape: `{stage['stage_shape']}`",
        f"- Today status: `{stage['today_status']}`",
        f"- Request manifest ID: `{binding['request_manifest_id']}`",
        f"- Candidate rows: `{binding['candidate_row_count']}`",
        f"- Assignment count: `{binding['assignment_count']}`",
        "",
        "## Request Preview",
        "",
        f"- Gate stage ID: `{manifest['gate_stage_id']}`",
        f"- Gate status: `{manifest['gate_status']}`",
        f"- Staging status: `{manifest['staging_status']}`",
        f"- Post-staging validation: `{manifest['post_staging_validation_status']}`",
        "",
        "## Blocked Reasons",
        "",
    ]
    for reason in blocked["blocked_reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the blocked run-scoped split fold-export request preview."
    )
    parser.add_argument(
        "--impl-order-contract",
        type=Path,
        default=DEFAULT_IMPL_ORDER_CONTRACT,
    )
    parser.add_argument(
        "--post-staging-gate-check-preview",
        type=Path,
        default=DEFAULT_POST_STAGING_GATE_CHECK_PREVIEW,
    )
    parser.add_argument(
        "--post-staging-gate-check-validation",
        type=Path,
        default=DEFAULT_POST_STAGING_GATE_CHECK_VALIDATION,
    )
    parser.add_argument("--staging-preview", type=Path, default=DEFAULT_STAGING_PREVIEW)
    parser.add_argument(
        "--split-engine-input-preview",
        type=Path,
        default=DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW,
    )
    parser.add_argument(
        "--split-fold-export-materialization-preview",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_MATERIALIZATION_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_split_fold_export_request_preview(
        _read_json(args.impl_order_contract),
        _read_json(args.post_staging_gate_check_preview),
        _read_json(args.post_staging_gate_check_validation),
        _read_json(args.staging_preview),
        _read_json(args.split_engine_input_preview),
        _read_json(args.split_fold_export_materialization_preview)
        if args.split_fold_export_materialization_preview.exists()
        else None,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
