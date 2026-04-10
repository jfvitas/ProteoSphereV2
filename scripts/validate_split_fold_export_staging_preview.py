from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGING_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p73_split_fold_export_staging_contract.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_STAGING_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_staging_preview.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_preview.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_GATE_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_validation.json"
)
DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_staging_validation.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_fold_export_staging_validation.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_split_fold_export_staging_validation(
    staging_contract: dict[str, Any],
    staging_preview: dict[str, Any],
    gate_preview: dict[str, Any],
    gate_validation: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    matches: list[str] = []

    required_values = staging_contract["staging_manifest_schema"]["required_values"]
    staging_manifest = staging_preview["staging_manifest"]
    blocked_report = staging_preview["blocked_report"]
    gate_binding = staging_preview["gate_binding"]
    split_assignment = split_engine_input_preview["assignment_binding"]
    contract_surface = staging_contract["staging_surface"]
    gate_validation_body = gate_validation["validation"]
    gate_validation_snapshot = gate_preview["validation_snapshot"]

    fold_materialized = bool(staging_preview["truth_boundary"]["cv_folds_materialized"])

    comparisons = [
        (
            "stage_id",
            staging_preview["stage"]["stage_id"],
            contract_surface["stage_id"],
        ),
        (
            "surface_id",
            staging_preview["stage"]["surface_id"],
            contract_surface["surface_id"],
        ),
        ("gate_id", gate_binding["gate_id"], required_values["gate_id"]),
        ("gate_surface", gate_binding["gate_surface"], required_values["gate_surface"]),
        (
            "gate_status",
            gate_binding["gate_status"],
            "open" if fold_materialized else required_values["gate_status"],
        ),
        (
            "candidate_row_count",
            staging_manifest["candidate_row_count"],
            required_values["candidate_row_count"],
        ),
        (
            "assignment_count",
            staging_manifest["assignment_count"],
            required_values["assignment_count"],
        ),
        (
            "split_group_counts",
            staging_manifest["split_group_counts"],
            required_values["split_group_counts"],
        ),
        (
            "row_level_split_counts",
            staging_manifest["row_level_split_counts"],
            required_values["row_level_split_counts"],
        ),
        (
            "largest_groups",
            staging_manifest["largest_groups"],
            gate_validation_snapshot["largest_groups"],
        ),
        (
            "blocked_reasons",
            blocked_report["blocked_reasons"],
            [] if fold_materialized else required_values["blocked_reasons"],
        ),
        ("validation_status", blocked_report["validation_status"], gate_validation["status"]),
        (
            "dry_run_validation_status",
            blocked_report["dry_run_validation_status"],
            gate_validation_snapshot["dry_run_validation_status"],
        ),
        (
            "dry_run_issue_count",
            blocked_report["dry_run_issue_count"],
            gate_validation_body["dry_run_issue_count"],
        ),
        (
            "input_assignment_count",
            staging_manifest["assignment_count"],
            split_assignment["assignment_count"],
        ),
        (
            "input_candidate_row_count",
            staging_manifest["candidate_row_count"],
            split_assignment["candidate_row_count"],
        ),
    ]
    for label, left, right in comparisons:
        if left == right:
            matches.append(label)
        else:
            issues.append(label)

    expected_stage_status = "complete" if fold_materialized else "blocked_report_emitted"
    if staging_preview["status"] != expected_stage_status:
        issues.append("staging_status")
    else:
        matches.append("staging_status")

    if staging_preview["stage"]["run_scoped_only"] is not True:
        issues.append("run_scoped_only")
    else:
        matches.append("run_scoped_only")

    if blocked_report["blocked"] is not (not fold_materialized):
        issues.append("blocked")
    else:
        matches.append("blocked")

    truth = staging_preview["truth_boundary"]
    if truth["cv_fold_export_unlocked"] is not fold_materialized:
        issues.append("cv_fold_export_unlocked")
    else:
        matches.append("cv_fold_export_unlocked")
    if truth["cv_folds_materialized"] is not fold_materialized:
        issues.append("cv_folds_materialized")
    else:
        matches.append("cv_folds_materialized")
    if truth["final_split_committed"] is not False:
        issues.append("final_split_committed")
    else:
        matches.append("final_split_committed")

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "split_fold_export_staging_validation",
        "schema_id": "proteosphere-split-fold-export-staging-validation-2026-04-01",
        "status": status,
        "validation": {
            "matches": matches,
            "issues": issues,
            "stage_status": staging_preview["status"],
            "gate_status": gate_binding["gate_status"],
            "candidate_row_count": staging_manifest["candidate_row_count"],
            "assignment_count": staging_manifest["assignment_count"],
            "dry_run_issue_count": blocked_report["dry_run_issue_count"],
            "blocked_reasons": blocked_report["blocked_reasons"],
        },
        "truth_boundary": {
            "summary": (
                "This validation checks that the scoped fold-export staging preview stays "
                "aligned with the contract, the gate preview, and the split-engine input "
                "preview. It accepts either the blocked staging state or a completed "
                "run-scoped fold materialization state."
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
        "# Split Fold Export Staging Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Stage status: `{validation['stage_status']}`",
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
        description="Validate the scoped split fold-export staging preview."
    )
    parser.add_argument("--staging-contract", type=Path, default=DEFAULT_STAGING_CONTRACT)
    parser.add_argument(
        "--split-fold-export-staging-preview",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_STAGING_PREVIEW,
    )
    parser.add_argument(
        "--split-fold-export-gate-preview",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_GATE_PREVIEW,
    )
    parser.add_argument(
        "--split-fold-export-gate-validation",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_GATE_VALIDATION,
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
    payload = build_split_fold_export_staging_validation(
        _read_json(args.staging_contract),
        _read_json(args.split_fold_export_staging_preview),
        _read_json(args.split_fold_export_gate_preview),
        _read_json(args.split_fold_export_gate_validation),
        _read_json(args.split_engine_input_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
