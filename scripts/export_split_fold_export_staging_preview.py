from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGING_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p73_split_fold_export_staging_contract.json"
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
DEFAULT_SPLIT_FOLD_EXPORT_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_staging_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_fold_export_staging_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_split_fold_export_staging_preview(
    staging_contract: dict[str, Any],
    split_fold_export_gate_preview: dict[str, Any],
    split_fold_export_gate_validation: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
    split_fold_export_materialization_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    staging_surface = staging_contract["staging_surface"]
    required_values = staging_contract["staging_manifest_schema"]["required_values"]
    gate = split_fold_export_gate_preview["gate"]
    gate_validation = split_fold_export_gate_validation["validation"]
    gate_validation_snapshot = split_fold_export_gate_preview["validation_snapshot"]
    gate_execution = split_fold_export_gate_preview["execution_snapshot"]
    gate_unlock = split_fold_export_gate_preview["unlock_readiness"]
    assignment_binding = split_engine_input_preview["assignment_binding"]
    recipe_binding = split_engine_input_preview["recipe_binding"]
    execution_readiness = split_engine_input_preview["execution_readiness"]

    stage_id = staging_surface["stage_id"]
    split_group_counts = gate_validation_snapshot["split_group_counts"]
    row_level_split_counts = gate_validation_snapshot["row_level_split_counts"]
    largest_groups = gate_validation_snapshot["largest_groups"]
    blocked_reasons = gate_unlock["blocked_reasons"]
    fold_export_materialized = bool(
        (split_fold_export_materialization_preview or {}).get("truth_boundary", {}).get(
            "cv_folds_materialized"
        )
    )
    gate_status = "open" if fold_export_materialized else staging_surface["current_state"]["gate_status"]

    return {
        "artifact_id": "split_fold_export_staging_preview",
        "schema_id": "proteosphere-split-fold-export-staging-preview-2026-04-01",
        "status": "complete" if fold_export_materialized else "blocked_report_emitted",
        "stage": {
            "stage_id": stage_id,
            "surface_id": staging_surface["surface_id"],
            "stage_shape": staging_surface["stage_shape"],
            "scope": staging_surface["scope"],
            "run_scoped_only": True,
        },
        "gate_binding": {
            "gate_id": gate["gate_id"],
            "gate_surface": gate["gate_surface"],
            "gate_status": gate_status,
            "cv_fold_export_unlocked": fold_export_materialized
            or staging_surface["current_state"]["cv_fold_export_unlocked"],
            "required_condition_count": gate["required_condition_count"],
        },
        "staging_manifest": {
            "staging_manifest_id": f"{stage_id}:{recipe_binding['recipe_id']}",
            "recipe_id": recipe_binding["recipe_id"],
            "assignment_artifact": "entity_split_assignment_preview",
            "input_artifact": recipe_binding["input_artifact"],
            "next_unlocked_stage": execution_readiness["next_unlocked_stage"],
            "candidate_row_count": assignment_binding["candidate_row_count"],
            "assignment_count": assignment_binding["assignment_count"],
            "split_group_counts": split_group_counts,
            "row_level_split_counts": row_level_split_counts,
            "largest_groups": largest_groups,
        },
        "blocked_report": {
            "blocked": not fold_export_materialized,
            "blocked_reasons": [] if fold_export_materialized else blocked_reasons,
            "validation_status": split_fold_export_gate_validation["status"],
            "dry_run_validation_status": gate_validation_snapshot[
                "dry_run_validation_status"
            ],
            "dry_run_issue_count": gate_validation["dry_run_issue_count"],
            "fold_export_ready": gate_execution["fold_export_ready"] or fold_export_materialized,
            "cv_folds_materialized": gate_execution["cv_folds_materialized"] or fold_export_materialized,
            "final_split_committed": gate_execution["final_split_committed"],
        },
        "contract_alignment": {
            "required_stage_id": required_values["gate_id"],
            "expected_gate_status": required_values["gate_status"],
            "expected_candidate_row_count": required_values["candidate_row_count"],
            "expected_assignment_count": required_values["assignment_count"],
            "expected_split_group_counts": required_values["split_group_counts"],
            "expected_row_level_split_counts": required_values["row_level_split_counts"],
            "expected_blocked_reasons": required_values["blocked_reasons"],
        },
        "truth_boundary": {
            "summary": (
                "This staging preview is the next executable fold-export surface, but it is "
                "still run-scoped-only and blocked. It preserves dry-run parity, emits a "
                "staging manifest shape, and stops before CV fold materialization or final "
                "split commitment."
            ),
            "run_scoped_only": True,
            "cv_fold_export_unlocked": fold_export_materialized,
            "cv_folds_materialized": fold_export_materialized,
            "final_split_committed": False,
            "release_split_promoted": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    stage = payload["stage"]
    gate = payload["gate_binding"]
    manifest = payload["staging_manifest"]
    blocked = payload["blocked_report"]
    lines = [
        "# Split Fold Export Staging Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Stage ID: `{stage['stage_id']}`",
        f"- Surface ID: `{stage['surface_id']}`",
        f"- Scope: `{stage['scope']}`",
        f"- Gate status: `{gate['gate_status']}`",
        f"- CV fold export unlocked: `{gate['cv_fold_export_unlocked']}`",
        "",
        "## Staging Manifest",
        "",
        f"- Manifest ID: `{manifest['staging_manifest_id']}`",
        f"- Recipe ID: `{manifest['recipe_id']}`",
        f"- Candidate rows: `{manifest['candidate_row_count']}`",
        f"- Assignment count: `{manifest['assignment_count']}`",
        f"- Next unlocked stage: `{manifest['next_unlocked_stage']}`",
        "",
        "## Blocked Report",
        "",
        f"- Validation status: `{blocked['validation_status']}`",
        f"- Dry-run validation status: `{blocked['dry_run_validation_status']}`",
        f"- Dry-run issue count: `{blocked['dry_run_issue_count']}`",
        f"- Fold export ready: `{blocked['fold_export_ready']}`",
        f"- CV folds materialized: `{blocked['cv_folds_materialized']}`",
        f"- Final split committed: `{blocked['final_split_committed']}`",
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
        description=(
            "Export a run-scoped split fold-export staging preview from the aligned "
            "dry-run surfaces without materializing CV folds."
        )
    )
    parser.add_argument("--staging-contract", type=Path, default=DEFAULT_STAGING_CONTRACT)
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
    payload = build_split_fold_export_staging_preview(
        _read_json(args.staging_contract),
        _read_json(args.split_fold_export_gate_preview),
        _read_json(args.split_fold_export_gate_validation),
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
