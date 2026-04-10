from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p68_split_fold_export_gate_contract.json"
)
DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_SPLIT_ENGINE_DRY_RUN_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_dry_run_validation.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_fold_export_gate_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_split_fold_export_gate_preview(
    gate_contract: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
    split_engine_dry_run_validation: dict[str, Any],
    split_fold_export_materialization_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = gate_contract["fold_export_gate"]
    gate_state = gate["current_state"]
    validation = split_engine_dry_run_validation["validation"]
    input_truth = split_engine_input_preview["truth_boundary"]
    assignment_binding = split_engine_input_preview["assignment_binding"]

    fold_export_materialized = bool(
        (split_fold_export_materialization_preview or {}).get("truth_boundary", {}).get(
            "cv_folds_materialized"
        )
    )
    blocked_reasons: list[str] = []
    if not fold_export_materialized and not gate_state["fold_export_ready"]:
        blocked_reasons.append("fold_export_ready=false")
    if split_engine_dry_run_validation["status"] != "aligned":
        blocked_reasons.append("dry_run_validation_not_aligned")
    if not fold_export_materialized and input_truth["cv_folds_materialized"] is False:
        blocked_reasons.append("cv_folds_materialized=false")
    if not fold_export_materialized and input_truth["final_split_committed"] is False:
        blocked_reasons.append("final_split_committed=false")
    cv_fold_export_unlocked = fold_export_materialized
    ready_for_fold_export = fold_export_materialized or not blocked_reasons

    return {
        "artifact_id": "split_fold_export_gate_preview",
        "schema_id": "proteosphere-split-fold-export-gate-preview-2026-04-01",
        "status": (
            "open_run_scoped_materialized"
            if fold_export_materialized
            else "blocked_pending_unlock"
        ),
        "gate": {
            "gate_id": gate["gate_id"],
            "gate_surface": gate["gate_surface"],
            "unlock_intent": gate["unlock_intent"],
            "required_condition_count": len(gate["required_unlock_conditions"]),
            "blocked_today_reason": gate["blocked_today_reason"],
        },
        "validation_snapshot": {
            "dry_run_validation_status": split_engine_dry_run_validation["status"],
            "dry_run_issue_count": len(validation["issues"]),
            "match_count": len(validation["matches"]),
            "candidate_row_count": validation["candidate_row_count"],
            "assignment_count": validation["assignment_count"],
            "split_group_counts": validation["split_group_counts"],
            "row_level_split_counts": validation["row_level_split_counts"],
            "largest_groups": validation["largest_groups"],
        },
        "execution_snapshot": {
            "next_unlocked_stage": split_engine_input_preview["execution_readiness"][
                "next_unlocked_stage"
            ],
            "group_row_count": assignment_binding["group_row_count"],
            "candidate_row_count": assignment_binding["candidate_row_count"],
            "assignment_count": assignment_binding["assignment_count"],
            "fold_export_ready": gate_state["fold_export_ready"] or fold_export_materialized,
            "cv_folds_materialized": input_truth["cv_folds_materialized"] or fold_export_materialized,
            "final_split_committed": input_truth["final_split_committed"],
        },
        "unlock_readiness": {
            "cv_fold_export_unlocked": cv_fold_export_unlocked,
            "blocked_reasons": blocked_reasons,
            "ready_for_fold_export": ready_for_fold_export,
            "run_scoped_fold_export_only": True,
        },
        "truth_boundary": {
            "summary": (
                "This preview makes the current fold-export boundary explicit. The dry-run "
                "split chain is aligned, and when a run-scoped fold export materialization "
                "exists it is treated as the authoritative unlock without promoting a release split."
            ),
            "report_only_contract_basis": True,
            "cv_folds_materialized": fold_export_materialized,
            "final_split_committed": False,
            "release_split_promoted": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    gate = payload["gate"]
    validation = payload["validation_snapshot"]
    execution = payload["execution_snapshot"]
    readiness = payload["unlock_readiness"]
    lines = [
        "# Split Fold Export Gate Preview",
        "",
        f"- Gate ID: `{gate['gate_id']}`",
        f"- Gate surface: `{gate['gate_surface']}`",
        f"- Status: `{payload['status']}`",
        f"- Required unlock conditions: `{gate['required_condition_count']}`",
        "",
        "## Validation Snapshot",
        "",
        f"- Dry-run validation status: `{validation['dry_run_validation_status']}`",
        f"- Dry-run issue count: `{validation['dry_run_issue_count']}`",
        f"- Match count: `{validation['match_count']}`",
        f"- Candidate rows: `{validation['candidate_row_count']}`",
        f"- Assignment count: `{validation['assignment_count']}`",
        "",
        "## Execution Snapshot",
        "",
        f"- Next unlocked stage: `{execution['next_unlocked_stage']}`",
        f"- Fold export ready: `{execution['fold_export_ready']}`",
        f"- CV folds materialized: `{execution['cv_folds_materialized']}`",
        f"- Final split committed: `{execution['final_split_committed']}`",
        "",
        "## Blocked Reasons",
        "",
    ]
    for reason in readiness["blocked_reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a live fold-export gate preview from the current split chain."
    )
    parser.add_argument("--gate-contract", type=Path, default=DEFAULT_GATE_CONTRACT)
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
    payload = build_split_fold_export_gate_preview(
        _read_json(args.gate_contract),
        _read_json(args.split_engine_input_preview),
        _read_json(args.split_engine_dry_run_validation),
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
