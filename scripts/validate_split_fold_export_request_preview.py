from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPL_ORDER_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p75_split_after_gate_check_impl_order.json"
)
DEFAULT_REQUEST_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_request_preview.json"
)
DEFAULT_POST_STAGING_GATE_CHECK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_preview.json"
)
DEFAULT_POST_STAGING_GATE_CHECK_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_validation.json"
)
DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_request_validation.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_fold_export_request_validation.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_split_fold_export_request_validation(
    impl_order_contract: dict[str, Any],
    request_preview: dict[str, Any],
    post_staging_gate_check_preview: dict[str, Any],
    post_staging_gate_check_validation: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    matches: list[str] = []

    request_stage = impl_order_contract["proposed_implementation_order"][0]
    live_grounding = impl_order_contract["current_live_grounding"]
    stage = request_preview["stage"]
    binding = request_preview["request_binding"]
    manifest = request_preview["request_manifest_preview"]
    blocked = request_preview["blocked_report"]
    gate_check = post_staging_gate_check_preview["gate_check"]
    gate_stage = post_staging_gate_check_preview["stage"]
    assignment = split_engine_input_preview["assignment_binding"]
    recipe = split_engine_input_preview["recipe_binding"]
    fold_materialized = bool(request_preview["truth_boundary"]["cv_folds_materialized"])

    comparisons = [
        ("stage_id", stage["stage_id"], request_stage["stage_id"]),
        ("stage_shape", stage["stage_shape"], request_stage["stage_shape"]),
        (
            "today_status",
            stage["today_status"],
            "fulfilled" if fold_materialized else request_stage["today_status"],
        ),
        ("recipe_id", binding["recipe_id"], recipe["recipe_id"]),
        ("input_artifact", binding["input_artifact"], recipe["input_artifact"]),
        (
            "linked_group_count",
            binding["linked_group_count"],
            assignment["group_row_count"],
        ),
        (
            "candidate_row_count",
            binding["candidate_row_count"],
            assignment["candidate_row_count"],
        ),
        ("assignment_count", binding["assignment_count"], assignment["assignment_count"]),
        ("gate_stage_id", manifest["gate_stage_id"], gate_stage["stage_id"]),
        (
            "gate_status",
            manifest["gate_status"],
            "open" if fold_materialized else gate_check["gate_status"],
        ),
        (
            "staging_status",
            manifest["staging_status"],
            post_staging_gate_check_preview["staging_parity"]["staging_status"],
        ),
        (
            "post_staging_validation_status",
            manifest["post_staging_validation_status"],
            post_staging_gate_check_validation["status"],
        ),
        (
            "live_gate_status",
            request_preview["live_grounding"]["gate_status"],
            "open" if fold_materialized else live_grounding["gate_status"],
        ),
        (
            "live_candidate_row_count",
            request_preview["live_grounding"]["candidate_row_count"],
            live_grounding["candidate_row_count"],
        ),
        (
            "live_assignment_count",
            request_preview["live_grounding"]["assignment_count"],
            live_grounding["assignment_count"],
        ),
        (
            "live_split_group_counts",
            request_preview["live_grounding"]["split_group_counts"],
            live_grounding["split_group_counts"],
        ),
        (
            "live_row_level_split_counts",
            request_preview["live_grounding"]["row_level_split_counts"],
            live_grounding["row_level_split_counts"],
        ),
    ]
    for label, left, right in comparisons:
        if left == right:
            matches.append(label)
        else:
            issues.append(label)

    expected_status = "complete" if fold_materialized else "blocked_report_emitted"
    if request_preview["status"] != expected_status:
        issues.append("status")
    else:
        matches.append("status")
    if stage["run_scoped_only"] is not True:
        issues.append("run_scoped_only")
    else:
        matches.append("run_scoped_only")
    if blocked["blocked"] is not (not fold_materialized):
        issues.append("blocked")
    else:
        matches.append("blocked")
    if blocked["cv_fold_export_unlocked"] is not fold_materialized:
        issues.append("cv_fold_export_unlocked")
    else:
        matches.append("cv_fold_export_unlocked")
    if blocked["cv_folds_materialized"] is not fold_materialized:
        issues.append("cv_folds_materialized")
    else:
        matches.append("cv_folds_materialized")
    if blocked["final_split_committed"] is not False:
        issues.append("final_split_committed")
    else:
        matches.append("final_split_committed")
    if blocked["gate_validation_issue_count"] != 0:
        issues.append("gate_validation_issue_count")
    else:
        matches.append("gate_validation_issue_count")

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "split_fold_export_request_validation",
        "schema_id": "proteosphere-split-fold-export-request-validation-2026-04-01",
        "status": status,
        "validation": {
            "matches": matches,
            "issues": issues,
            "stage_status": request_preview["status"],
            "gate_status": manifest["gate_status"],
            "candidate_row_count": binding["candidate_row_count"],
            "assignment_count": binding["assignment_count"],
            "blocked_reasons": blocked["blocked_reasons"],
        },
        "truth_boundary": {
            "summary": (
            "This validation checks the blocked run-scoped fold-export request preview "
            "against the post-staging gate check and split-engine input surfaces. "
            "It accepts either the blocked request state or a fulfilled run-scoped "
            "fold materialization state."
            ),
            "run_scoped_only": True,
            "cv_fold_export_unlocked": fold_materialized,
            "cv_folds_materialized": fold_materialized,
            "final_split_committed": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    lines = [
        "# Split Fold Export Request Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Stage status: `{validation['stage_status']}`",
        f"- Gate status: `{validation['gate_status']}`",
        f"- Candidate rows: `{validation['candidate_row_count']}`",
        f"- Assignment count: `{validation['assignment_count']}`",
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
        description="Validate the blocked run-scoped split fold-export request preview."
    )
    parser.add_argument(
        "--impl-order-contract",
        type=Path,
        default=DEFAULT_IMPL_ORDER_CONTRACT,
    )
    parser.add_argument(
        "--request-preview",
        type=Path,
        default=DEFAULT_REQUEST_PREVIEW,
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
    parser.add_argument(
        "--split-engine-input-preview",
        type=Path,
        default=DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_split_fold_export_request_validation(
        _read_json(args.impl_order_contract),
        _read_json(args.request_preview),
        _read_json(args.post_staging_gate_check_preview),
        _read_json(args.post_staging_gate_check_validation),
        _read_json(args.split_engine_input_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
