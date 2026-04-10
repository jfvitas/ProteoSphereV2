from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXT_STAGE_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p74_split_post_staging_next_step.json"
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
DEFAULT_GATE_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_validation.json"
)
DEFAULT_SPLIT_ENGINE_INPUT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_post_staging_gate_check_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_split_post_staging_gate_check_preview(
    next_stage_contract: dict[str, Any],
    staging_preview: dict[str, Any],
    staging_validation: dict[str, Any],
    gate_preview: dict[str, Any],
    gate_validation: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
    split_fold_export_materialization_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    next_stage = next_stage_contract["next_safest_executable_stage"]
    contract_grounding = next_stage_contract["current_live_grounding"]
    staging_manifest = staging_preview["staging_manifest"]
    staging_blocked = staging_preview["blocked_report"]
    staging_validation_body = staging_validation["validation"]
    gate_validation_body = gate_validation["validation"]
    input_assignment = split_engine_input_preview["assignment_binding"]
    fold_export_materialized = bool(
        (split_fold_export_materialization_preview or {}).get("truth_boundary", {}).get(
            "cv_folds_materialized"
        )
    )

    return {
        "artifact_id": "split_post_staging_gate_check_preview",
        "schema_id": "proteosphere-split-post-staging-gate-check-preview-2026-04-01",
        "status": "complete" if fold_export_materialized else "blocked_report_emitted",
        "stage": {
            "stage_id": next_stage["stage_id"],
            "stage_shape": next_stage["stage_shape"],
            "today_output": next_stage["today_output"],
            "run_scoped_only": True,
        },
        "gate_check": {
            "gate_id": contract_grounding["gate_id"],
            "gate_surface": contract_grounding["gate_surface"],
            "gate_status": "open" if fold_export_materialized else contract_grounding["gate_status"],
            "fold_export_ready": contract_grounding["fold_export_ready"],
            "cv_fold_export_unlocked": fold_export_materialized,
        },
        "staging_parity": {
            "staging_status": staging_preview["status"],
            "staging_validation_status": staging_validation["status"],
            "dry_run_validation_status": staging_blocked["dry_run_validation_status"],
            "dry_run_issue_count": staging_blocked["dry_run_issue_count"],
            "candidate_row_count": staging_manifest["candidate_row_count"],
            "assignment_count": staging_manifest["assignment_count"],
            "split_group_counts": staging_manifest["split_group_counts"],
            "row_level_split_counts": staging_manifest["row_level_split_counts"],
            "largest_groups": staging_manifest["largest_groups"],
        },
        "blocked_report": {
            "blocked": not fold_export_materialized,
            "blocked_reasons": [] if fold_export_materialized else staging_blocked["blocked_reasons"],
            "staging_validation_issue_count": len(staging_validation_body["issues"]),
            "gate_validation_issue_count": len(gate_validation_body["issues"]),
            "cv_folds_materialized": staging_preview["truth_boundary"][
                "cv_folds_materialized"
            ],
            "final_split_committed": staging_preview["truth_boundary"][
                "final_split_committed"
            ],
        },
        "input_parity": {
            "input_assignment_count": input_assignment["assignment_count"],
            "input_candidate_row_count": input_assignment["candidate_row_count"],
            "matches_staging_assignment_count": (
                input_assignment["assignment_count"] == staging_manifest["assignment_count"]
            ),
            "matches_staging_candidate_row_count": (
                input_assignment["candidate_row_count"]
                == staging_manifest["candidate_row_count"]
            ),
        },
        "truth_boundary": {
            "summary": (
            "This post-staging gate check preview revalidates the staging handoff "
            "against the fold-export gate. It remains run-scoped and, when fold "
            "materialization exists, reflects the executed non-committing export."
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
    gate = payload["gate_check"]
    parity = payload["staging_parity"]
    blocked = payload["blocked_report"]
    lines = [
        "# Split Post-Staging Gate Check Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Stage ID: `{stage['stage_id']}`",
        f"- Stage shape: `{stage['stage_shape']}`",
        f"- Today output: `{stage['today_output']}`",
        f"- Gate status: `{gate['gate_status']}`",
        f"- CV fold export unlocked: `{gate['cv_fold_export_unlocked']}`",
        "",
        "## Staging Parity",
        "",
        f"- Staging status: `{parity['staging_status']}`",
        f"- Staging validation status: `{parity['staging_validation_status']}`",
        f"- Dry-run validation status: `{parity['dry_run_validation_status']}`",
        f"- Candidate rows: `{parity['candidate_row_count']}`",
        f"- Assignment count: `{parity['assignment_count']}`",
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
        description="Export the next post-staging fold-export gate-check preview."
    )
    parser.add_argument(
        "--next-stage-contract",
        type=Path,
        default=DEFAULT_NEXT_STAGE_CONTRACT,
    )
    parser.add_argument("--staging-preview", type=Path, default=DEFAULT_STAGING_PREVIEW)
    parser.add_argument(
        "--staging-validation",
        type=Path,
        default=DEFAULT_STAGING_VALIDATION,
    )
    parser.add_argument("--gate-preview", type=Path, default=DEFAULT_GATE_PREVIEW)
    parser.add_argument(
        "--gate-validation",
        type=Path,
        default=DEFAULT_GATE_VALIDATION,
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
    payload = build_split_post_staging_gate_check_preview(
        _read_json(args.next_stage_contract),
        _read_json(args.staging_preview),
        _read_json(args.staging_validation),
        _read_json(args.gate_preview),
        _read_json(args.gate_validation),
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
