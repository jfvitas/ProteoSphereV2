from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXT_STAGE_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p74_split_post_staging_next_step.json"
)
DEFAULT_POST_STAGING_GATE_CHECK_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_preview.json"
)
DEFAULT_STAGING_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_staging_preview.json"
)
DEFAULT_STAGING_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_staging_validation.json"
)
DEFAULT_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_preview.json"
)
DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_validation.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_post_staging_gate_check_validation.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_split_post_staging_gate_check_validation(
    next_stage_contract: dict[str, Any],
    gate_check_preview: dict[str, Any],
    staging_preview: dict[str, Any],
    staging_validation: dict[str, Any],
    gate_preview: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    matches: list[str] = []

    next_stage = next_stage_contract["next_safest_executable_stage"]
    grounding = next_stage_contract["current_live_grounding"]
    stage = gate_check_preview["stage"]
    gate_check = gate_check_preview["gate_check"]
    parity = gate_check_preview["staging_parity"]
    blocked = gate_check_preview["blocked_report"]
    input_parity = gate_check_preview["input_parity"]
    fold_materialized = bool(gate_check_preview["truth_boundary"]["cv_folds_materialized"])

    comparisons = [
        ("stage_id", stage["stage_id"], next_stage["stage_id"]),
        ("stage_shape", stage["stage_shape"], next_stage["stage_shape"]),
        ("today_output", stage["today_output"], next_stage["today_output"]),
        ("gate_id", gate_check["gate_id"], grounding["gate_id"]),
        ("gate_surface", gate_check["gate_surface"], grounding["gate_surface"]),
        (
            "gate_status",
            gate_check["gate_status"],
            "open" if fold_materialized else grounding["gate_status"],
        ),
        (
            "fold_export_ready",
            gate_check["fold_export_ready"],
            grounding["fold_export_ready"],
        ),
        ("staging_status", parity["staging_status"], staging_preview["status"]),
        (
            "staging_validation_status",
            parity["staging_validation_status"],
            staging_validation["status"],
        ),
        (
            "dry_run_validation_status",
            parity["dry_run_validation_status"],
            gate_preview["validation_snapshot"]["dry_run_validation_status"],
        ),
        (
            "candidate_row_count",
            parity["candidate_row_count"],
            staging_preview["staging_manifest"]["candidate_row_count"],
        ),
        (
            "assignment_count",
            parity["assignment_count"],
            staging_preview["staging_manifest"]["assignment_count"],
        ),
        (
            "split_group_counts",
            parity["split_group_counts"],
            staging_preview["staging_manifest"]["split_group_counts"],
        ),
        (
            "row_level_split_counts",
            parity["row_level_split_counts"],
            staging_preview["staging_manifest"]["row_level_split_counts"],
        ),
        (
            "largest_groups",
            parity["largest_groups"],
            staging_preview["staging_manifest"]["largest_groups"],
        ),
        (
            "input_assignment_count",
            input_parity["input_assignment_count"],
            split_engine_input_preview["assignment_binding"]["assignment_count"],
        ),
        (
            "input_candidate_row_count",
            input_parity["input_candidate_row_count"],
            split_engine_input_preview["assignment_binding"]["candidate_row_count"],
        ),
    ]
    for label, left, right in comparisons:
        if left == right:
            matches.append(label)
        else:
            issues.append(label)

    expected_stage_status = "complete" if fold_materialized else "blocked_report_emitted"
    if gate_check_preview["status"] != expected_stage_status:
        issues.append("status")
    else:
        matches.append("status")
    if stage["run_scoped_only"] is not True:
        issues.append("run_scoped_only")
    else:
        matches.append("run_scoped_only")
    if gate_check["cv_fold_export_unlocked"] is not fold_materialized:
        issues.append("cv_fold_export_unlocked")
    else:
        matches.append("cv_fold_export_unlocked")
    if blocked["blocked"] is not (not fold_materialized):
        issues.append("blocked")
    else:
        matches.append("blocked")
    if blocked["staging_validation_issue_count"] != 0:
        issues.append("staging_validation_issue_count")
    else:
        matches.append("staging_validation_issue_count")
    if blocked["gate_validation_issue_count"] != 0:
        issues.append("gate_validation_issue_count")
    else:
        matches.append("gate_validation_issue_count")
    if input_parity["matches_staging_assignment_count"] is not True:
        issues.append("matches_staging_assignment_count")
    else:
        matches.append("matches_staging_assignment_count")
    if input_parity["matches_staging_candidate_row_count"] is not True:
        issues.append("matches_staging_candidate_row_count")
    else:
        matches.append("matches_staging_candidate_row_count")

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "split_post_staging_gate_check_validation",
        "schema_id": "proteosphere-split-post-staging-gate-check-validation-2026-04-01",
        "status": status,
        "validation": {
            "matches": matches,
            "issues": issues,
            "stage_status": gate_check_preview["status"],
            "gate_status": gate_check["gate_status"],
            "candidate_row_count": parity["candidate_row_count"],
            "assignment_count": parity["assignment_count"],
            "blocked_reasons": blocked["blocked_reasons"],
        },
        "truth_boundary": {
            "summary": (
                "This validation checks the post-staging gate-check preview against the "
                "current staging and split-input surfaces. It accepts either the blocked "
                "gate-check state or a completed run-scoped fold materialization state."
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
        "# Split Post-Staging Gate Check Validation",
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
        description="Validate the split post-staging gate-check preview."
    )
    parser.add_argument(
        "--next-stage-contract",
        type=Path,
        default=DEFAULT_NEXT_STAGE_CONTRACT,
    )
    parser.add_argument(
        "--post-staging-gate-check-preview",
        type=Path,
        default=DEFAULT_POST_STAGING_GATE_CHECK_PREVIEW,
    )
    parser.add_argument("--staging-preview", type=Path, default=DEFAULT_STAGING_PREVIEW)
    parser.add_argument(
        "--staging-validation",
        type=Path,
        default=DEFAULT_STAGING_VALIDATION,
    )
    parser.add_argument("--gate-preview", type=Path, default=DEFAULT_GATE_PREVIEW)
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
    payload = build_split_post_staging_gate_check_validation(
        _read_json(args.next_stage_contract),
        _read_json(args.post_staging_gate_check_preview),
        _read_json(args.staging_preview),
        _read_json(args.staging_validation),
        _read_json(args.gate_preview),
        _read_json(args.split_engine_input_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
