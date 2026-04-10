from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPLIT_FOLD_EXPORT_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_preview.json"
)
DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_SPLIT_ENGINE_DRY_RUN_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_dry_run_validation.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_validation.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_fold_export_gate_validation.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_split_fold_export_gate_validation(
    split_fold_export_gate_preview: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
    split_engine_dry_run_validation: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    matches: list[str] = []

    gate_validation = split_fold_export_gate_preview["validation_snapshot"]
    gate_execution = split_fold_export_gate_preview["execution_snapshot"]
    gate_unlock = split_fold_export_gate_preview["unlock_readiness"]
    input_assignment = split_engine_input_preview["assignment_binding"]
    input_truth = split_engine_input_preview["truth_boundary"]
    dry_run_validation = split_engine_dry_run_validation["validation"]
    dry_run_truth = split_engine_dry_run_validation["truth_boundary"]

    comparisons = [
        (
            "dry_run_validation_status",
            gate_validation["dry_run_validation_status"],
            split_engine_dry_run_validation["status"],
        ),
        (
            "candidate_row_count",
            gate_validation["candidate_row_count"],
            dry_run_validation["candidate_row_count"],
        ),
        (
            "assignment_count",
            gate_validation["assignment_count"],
            dry_run_validation["assignment_count"],
        ),
        (
            "split_group_counts",
            gate_validation["split_group_counts"],
            dry_run_validation["split_group_counts"],
        ),
        (
            "row_level_split_counts",
            gate_validation["row_level_split_counts"],
            dry_run_validation["row_level_split_counts"],
        ),
        (
            "largest_groups",
            gate_validation["largest_groups"],
            dry_run_validation["largest_groups"],
        ),
        (
            "execution_candidate_row_count",
            gate_execution["candidate_row_count"],
            input_assignment["candidate_row_count"],
        ),
        (
            "execution_assignment_count",
            gate_execution["assignment_count"],
            input_assignment["assignment_count"],
        ),
        (
            "cv_folds_materialized",
            gate_execution["cv_folds_materialized"],
            input_truth["cv_folds_materialized"],
        ),
        (
            "final_split_committed",
            gate_execution["final_split_committed"],
            dry_run_truth["final_split_committed"],
        ),
    ]
    for label, left, right in comparisons:
        if left == right:
            matches.append(label)
        else:
            issues.append(label)

    fold_materialized = bool(gate_execution["cv_folds_materialized"])
    expected_unlocked = fold_materialized
    if gate_unlock["cv_fold_export_unlocked"] is not expected_unlocked:
        issues.append("cv_fold_export_unlocked")
    else:
        matches.append("cv_fold_export_unlocked")

    expected_ready = fold_materialized or gate_execution["fold_export_ready"]
    if gate_unlock["ready_for_fold_export"] is not bool(expected_ready):
        issues.append("ready_for_fold_export")
    else:
        matches.append("ready_for_fold_export")

    expected_blocked_reasons = (
        set()
        if fold_materialized
        else {
            "fold_export_ready=false",
            "cv_folds_materialized=false",
            "final_split_committed=false",
        }
    )
    blocked_reasons = set(gate_unlock.get("blocked_reasons", []))
    if blocked_reasons == expected_blocked_reasons:
        matches.append("blocked_reasons")
    else:
        issues.append("blocked_reasons")

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "split_fold_export_gate_validation",
        "schema_id": "proteosphere-split-fold-export-gate-validation-2026-04-01",
        "status": status,
        "validation": {
            "matches": matches,
            "issues": issues,
            "gate_status": split_fold_export_gate_preview["status"],
            "required_condition_count": split_fold_export_gate_preview["gate"][
                "required_condition_count"
            ],
            "candidate_row_count": gate_validation["candidate_row_count"],
            "assignment_count": gate_validation["assignment_count"],
            "dry_run_issue_count": gate_validation["dry_run_issue_count"],
            "blocked_reasons": gate_unlock["blocked_reasons"],
        },
        "truth_boundary": {
            "summary": (
                "This validation checks parity between the fold-export gate preview and the "
                "current split-engine input and dry-run validation surfaces. It accepts "
                "either the blocked pre-materialization state or a completed run-scoped "
                "fold export materialization."
            ),
            "cv_fold_export_unlocked": expected_unlocked,
            "cv_folds_materialized": fold_materialized,
            "final_split_committed": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    lines = [
        "# Split Fold Export Gate Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Gate status: `{validation['gate_status']}`",
        f"- Candidate rows: `{validation['candidate_row_count']}`",
        f"- Assignment count: `{validation['assignment_count']}`",
        f"- Dry-run issue count: `{validation['dry_run_issue_count']}`",
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
    lines.extend(["", "## Blocked Reasons", ""])
    for reason in validation["blocked_reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate parity for the live split fold-export gate preview."
    )
    parser.add_argument(
        "--split-fold-export-gate-preview",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_GATE_PREVIEW,
    )
    parser.add_argument(
        "--split-engine-input-preview",
        type=Path,
        default=DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW,
    )
    parser.add_argument(
        "--split-engine-dry-run-validation",
        type=Path,
        default=DEFAULT_SPLIT_ENGINE_DRY_RUN_VALIDATION,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_split_fold_export_gate_validation(
        _read_json(args.split_fold_export_gate_preview),
        _read_json(args.split_engine_input_preview),
        _read_json(args.split_engine_dry_run_validation),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
