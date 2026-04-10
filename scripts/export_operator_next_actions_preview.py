from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIGAND_DECISION = (
    REPO_ROOT / "artifacts" / "status" / "next_real_ligand_row_decision_preview.json"
)
DEFAULT_STRUCTURE_VALIDATION = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "structure_followup_single_accession_validation_preview.json"
)
DEFAULT_SPLIT_REQUEST = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_request_preview.json"
)
DEFAULT_DUPLICATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_first_execution_preview.json"
)
DEFAULT_DUPLICATE_DELETE_READY_MANIFEST = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "duplicate_cleanup_delete_ready_manifest_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "operator_next_actions_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "operator_next_actions_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _duplicate_lane_status(delete_ready_manifest: dict[str, Any]) -> str:
    if int(delete_ready_manifest.get("action_count") or 0) <= 0:
        return "refresh_required_after_consumed_preview_batch"
    return str(delete_ready_manifest.get("preview_manifest_status") or "report_only")


def _duplicate_lane_next_stage(delete_ready_manifest: dict[str, Any]) -> str:
    if int(delete_ready_manifest.get("action_count") or 0) <= 0:
        return "refresh_exact_duplicate_plan_before_next_execution"
    return "wait_for_separate_mutation_authorization"


def build_operator_next_actions_preview(
    ligand_decision: dict[str, Any],
    structure_validation: dict[str, Any],
    split_request: dict[str, Any],
    duplicate_preview: dict[str, Any],
    duplicate_delete_ready_manifest: dict[str, Any],
) -> dict[str, Any]:
    selected_probe = ligand_decision.get("selected_accession_probe_criteria") or {}
    duplicate_constraints = duplicate_delete_ready_manifest.get("constraint_checks") or {}
    duplicate_action_count = int(duplicate_delete_ready_manifest.get("action_count") or 0)

    prioritized_actions = [
        {
            "rank": 1,
            "lane": "ligand",
            "status": ligand_decision["selected_accession_gate_status"],
            "accession": ligand_decision["selected_accession"],
            "next_truthful_stage": "hold_until_validated_local_evidence_exists",
            "detail": {
                "selected_accession_gate_status": ligand_decision[
                    "selected_accession_gate_status"
                ],
                "best_next_action": selected_probe.get("best_next_action"),
                "best_next_source": selected_probe.get("best_next_source"),
                "source_classification": selected_probe.get("source_classification"),
                "gap_probe_classification": selected_probe.get(
                    "gap_probe_classification"
                ),
                "fallback_accession": ligand_decision["fallback_accession"],
                "fallback_accession_gate_status": ligand_decision[
                    "fallback_accession_gate_status"
                ],
                "fallback_trigger_rule": ligand_decision["fallback_trigger_rule"],
                "current_grounded_accessions": ligand_decision[
                    "current_grounded_accessions"
                ],
                "candidate_only_rows_non_governing": ligand_decision[
                    "truth_boundary"
                ].get("candidate_only_rows_non_governing"),
            },
            "blocked_for_release": True,
        },
        {
            "rank": 2,
            "lane": "structure",
            "status": structure_validation["status"],
            "accession": structure_validation["selected_accession"],
            "next_truthful_stage": "single_accession_candidate_only_promotion",
            "detail": {
                "deferred_accession": structure_validation["deferred_accession"],
                "candidate_variant_anchor_count": structure_validation[
                    "candidate_variant_anchor_count"
                ],
                "direct_structure_backed_join_certified": structure_validation[
                    "direct_structure_backed_join_certified"
                ],
            },
            "blocked_for_release": True,
        },
        {
            "rank": 3,
            "lane": "split",
            "status": split_request["status"],
            "accession": None,
            "next_truthful_stage": "wait_for_unlock_gate_before_request_emission",
            "detail": {
                "request_scope": split_request["stage"]["run_scoped_only"],
                "cv_fold_export_unlocked": split_request["truth_boundary"][
                    "cv_fold_export_unlocked"
                ],
                "cv_folds_materialized": split_request["truth_boundary"][
                    "cv_folds_materialized"
                ],
            },
            "blocked_for_release": True,
        },
        {
            "rank": 4,
            "lane": "duplicate_cleanup",
            "status": _duplicate_lane_status(duplicate_delete_ready_manifest),
            "accession": None,
            "next_truthful_stage": _duplicate_lane_next_stage(
                duplicate_delete_ready_manifest
            ),
            "detail": {
                "batch_size_limit": duplicate_preview["batch_size_limit"],
                "duplicate_class": duplicate_preview["duplicate_class"],
                "delete_enabled": duplicate_preview["truth_boundary"]["delete_enabled"],
                "execution_blocked": duplicate_delete_ready_manifest[
                    "execution_blocked"
                ],
                "preview_manifest_status": duplicate_delete_ready_manifest.get(
                    "preview_manifest_status"
                ),
                "delete_ready_action_count": duplicate_action_count,
                "all_constraints_satisfied_preview": duplicate_constraints.get(
                    "all_constraints_satisfied_preview"
                ),
                "refresh_required": duplicate_action_count <= 0,
            },
            "blocked_for_release": True,
        },
    ]
    return {
        "artifact_id": "operator_next_actions_preview",
        "schema_id": "proteosphere-operator-next-actions-preview-2026-04-02",
        "status": "complete",
        "row_count": len(prioritized_actions),
        "prioritized_actions": prioritized_actions,
        "truth_boundary": {
            "summary": (
                "This is an operator-only consolidation of the current next-step surfaces. "
                "It does not certify structure joins, does not emit a second grounded ligand "
                "accession, does not unlock fold export, and does not authorize duplicate "
                "cleanup mutation."
            ),
            "report_only": True,
            "ready_for_operator_preview": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Operator Next Actions Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Action count: `{payload['row_count']}`",
        "",
        "## Prioritized Actions",
        "",
    ]
    for row in payload["prioritized_actions"]:
        target = row["accession"] if row["accession"] is not None else row["lane"]
        lines.append(
            f"- `{row['rank']}` `{row['lane']}` -> `{target}` / "
            f"`{row['next_truthful_stage']}` / status `{row['status']}`"
        )
        lines.append(f"  detail: `{json.dumps(row['detail'], sort_keys=True)}`")
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}", ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a compact operator next-actions preview."
    )
    parser.add_argument("--ligand-decision", type=Path, default=DEFAULT_LIGAND_DECISION)
    parser.add_argument(
        "--structure-validation",
        type=Path,
        default=DEFAULT_STRUCTURE_VALIDATION,
    )
    parser.add_argument("--split-request", type=Path, default=DEFAULT_SPLIT_REQUEST)
    parser.add_argument(
        "--duplicate-preview",
        type=Path,
        default=DEFAULT_DUPLICATE_PREVIEW,
    )
    parser.add_argument(
        "--duplicate-delete-ready-manifest",
        type=Path,
        default=DEFAULT_DUPLICATE_DELETE_READY_MANIFEST,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_operator_next_actions_preview(
        _read_json(args.ligand_decision),
        _read_json(args.structure_validation),
        _read_json(args.split_request),
        _read_json(args.duplicate_preview),
        _read_json(args.duplicate_delete_ready_manifest),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
